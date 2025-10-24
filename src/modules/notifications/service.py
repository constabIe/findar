"""
Notification service for sending alerts through email and Telegram.

This module renders templates, sends notifications via email and Telegram,
persists deliveries and attempts via the repository and logs all actions.

Notes:
- Metrics hooks are present as function calls; integrate Prometheus in reporting later.
- Uses dedicated sender classes (EmailSender, TelegramSender) for channel-specific logic.
- Errors use core.exceptions.NotificationError where appropriate.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

if TYPE_CHECKING:
    # Imported for type checking only; runtime uses a session from the app
    from sqlalchemy.ext.asyncio import AsyncSession  # pragma: no cover
else:
    AsyncSession = Any

from sqlalchemy import select

from src.core.exceptions import NotificationError
from src.core.logging import get_logger
from src.modules.notifications.enums import (
    NotificationChannel,
    NotificationStatus,
)
from src.modules.notifications.models import (
    NotificationTemplate,
)
from src.modules.notifications.repository import NotificationRepository
from src.modules.notifications.schemas import NotificationDeliveryCreate
from src.modules.notifications.senders import EmailSender, TelegramSender
from src.modules.reporting.metrics import (
    increment_error_counter,
    observe_notification_time,
)
from src.modules.users.repository import UserRepository
from src.storage.models import Rule as RuleModel

logger = get_logger("notifications")


class NotificationService:
    """
    Service for sending notifications via email and Telegram.

    Responsibilities:
    - Render templates according to template flags
    - Create delivery records via repository
    - Send messages via channel-specific senders (email, telegram)
    - Persist attempts and update delivery status
    - Be fault-tolerant: failures are recorded, not raised to break processing pipeline
    """

    def __init__(self, db_session: AsyncSession) -> None:
        """
        Initialize NotificationService.

        Args:
            db_session: Async DB session used by repository
        """
        self.db_session = db_session
        self.repo = NotificationRepository(db_session)

        # Initialize channel senders
        self.email_sender = EmailSender()
        self.telegram_sender = TelegramSender()

    async def send_fraud_alert(
        self,
        transaction_data: Dict[str, Any],
        evaluation_result: Dict[str, Any],
        correlation_id: str,
    ) -> List[UUID]:
        """
        For each matched rule in evaluation_result:

        - Load the rule from the DB and find the rule's author (created_by_user_id)
        - Load the user record
        - Always create an EMAIL delivery to the user's email informing about the rule violation
        - For Telegram:
            - If the user's telegram_alias is present in DB -> send a telegram message notifying
              that their rule was violated
            - If telegram_alias is not present -> send a telegram message (using telegram_id)
              asking the user to register on the website (bot: @findar_linear_bot)

        Returns list of created delivery IDs. Function is fault-tolerant and logs errors.
        """
        start = datetime.utcnow()
        created_ids: List[UUID] = []

        # Pull matched rules from possible keys used by different modules
        matched = (
            evaluation_result.get("matched_rules")
            or evaluation_result.get("triggered_rules")
            or evaluation_result.get("rule_results")
            or []
        )

        if not matched:
            logger.debug(
                "No matched rules in evaluation_result - nothing to notify",
                component="notifications",
                correlation_id=correlation_id,
            )
            return []

        for rule_entry in matched:
            try:
                # rule_entry can be a dict with 'rule_id' or 'id'
                rule_id_raw = rule_entry.get("rule_id") or rule_entry.get("id")
                if not rule_id_raw:
                    logger.debug(
                        "Skipping rule entry without id",
                        component="notifications",
                        entry=str(rule_entry),
                        correlation_id=correlation_id,
                    )
                    continue

                rule_id = UUID(str(rule_id_raw))

                # Load rule object from DB
                try:
                    res = await self.db_session.execute(
                        select(RuleModel).where(RuleModel.id == rule_id)
                    )
                    rule_obj = res.scalars().first()
                except Exception:
                    logger.exception(
                        "Failed to load rule from DB",
                        component="notifications",
                        rule_id=str(rule_id),
                        correlation_id=correlation_id,
                    )
                    increment_error_counter("rule_load_error")
                    continue

                if not rule_obj:
                    logger.warning(
                        "Rule not found in DB",
                        component="notifications",
                        rule_id=str(rule_id),
                        correlation_id=correlation_id,
                    )
                    continue

                author_id = getattr(rule_obj, "created_by_user_id", None)
                if not author_id:
                    logger.warning(
                        "Rule has no author set",
                        component="notifications",
                        rule_id=str(rule_id),
                        correlation_id=correlation_id,
                    )
                    continue

                # Load the user record
                try:
                    user_repo = UserRepository(self.db_session)
                    user = await user_repo.get_user_by_id(author_id)
                except Exception:
                    logger.exception(
                        "Failed to load user for rule author",
                        component="notifications",
                        user_id=str(author_id),
                        rule_id=str(rule_id),
                        correlation_id=correlation_id,
                    )
                    increment_error_counter("user_load_error")
                    continue

                if not user:
                    logger.warning(
                        "Author user not found",
                        component="notifications",
                        user_id=str(author_id),
                        rule_id=str(rule_id),
                        correlation_id=correlation_id,
                    )
                    continue

                txn_id = (
                    UUID(str(transaction_data.get("id")))
                    if transaction_data.get("id")
                    else None
                )

                # Always send email (if available)
                if getattr(user, "email", None) and txn_id:
                    try:
                        subject = f"Rule violated: {rule_obj.name}"
                        body = (
                            f"Hello,\n\nYour rule '{rule_obj.name}' was triggered by transaction {transaction_data.get('id')}.\n"
                            "Please review the transaction in the admin panel.\n\nRegards,\nFindar"
                        )

                        payload = NotificationDeliveryCreate(
                            transaction_id=txn_id,
                            template_id=None,
                            channel=NotificationChannel.EMAIL,
                            subject=subject,
                            body=body,
                            recipients=[user.email],
                            priority=1,
                            scheduled_at=None,
                            metadata={
                                "correlation_id": correlation_id,
                                "rule_id": str(rule_id),
                                "rule_name": rule_obj.name,
                            },
                        )

                        await self._create_and_schedule_delivery(payload, created_ids)
                    except Exception:
                        logger.exception(
                            "Failed to create/send email delivery for rule author",
                            component="notifications",
                            user_id=str(author_id),
                            rule_id=str(rule_id),
                            correlation_id=correlation_id,
                        )
                        increment_error_counter("delivery_create_error")

                # Telegram send: users always have telegram_id; check alias presence
                try:
                    # Prefer numeric telegram_id for direct messages
                    tg_recipient = None
                    if getattr(user, "telegram_id", None):
                        tg_recipient = [str(user.telegram_id)]
                    elif getattr(user, "telegram_alias", None):
                        alias = getattr(user, "telegram_alias")
                        if alias and not alias.startswith("@"):
                            alias = f"@{alias}"
                        tg_recipient = [alias]

                    if tg_recipient:
                        if getattr(user, "telegram_alias", None):
                            tg_body = f"Your rule '{rule_obj.name}' was violated by transaction {transaction_data.get('id')}."
                        else:
                            # Ask user to register on the website (bot will be the sender)
                            tg_body = "Please register on our website to receive full alerts and start the bot @findar_linear_bot."

                        payload = NotificationDeliveryCreate(
                            transaction_id=txn_id
                            or UUID(str(transaction_data.get("id")))
                            if transaction_data.get("id")
                            else None,
                            template_id=None,
                            channel=NotificationChannel.TELEGRAM,
                            subject=None,
                            body=tg_body,
                            recipients=tg_recipient,
                            priority=1,
                            scheduled_at=None,
                            metadata={
                                "correlation_id": correlation_id,
                                "rule_id": str(rule_id),
                                "rule_name": rule_obj.name,
                            },
                        )

                        await self._create_and_schedule_delivery(payload, created_ids)

                except Exception:
                    logger.exception(
                        "Failed to create/send telegram delivery for rule author",
                        component="notifications",
                        user_id=str(author_id),
                        rule_id=str(rule_id),
                        correlation_id=correlation_id,
                    )
                    increment_error_counter("delivery_create_error")

            except Exception:
                logger.exception(
                    "Unexpected error while creating notifications for matched rule",
                    component="notifications",
                    entry=str(rule_entry),
                    correlation_id=correlation_id,
                )
                increment_error_counter("notification_unexpected_error")

        duration = (datetime.utcnow() - start).total_seconds()
        observe_notification_time(duration)

        logger.info(
            "Finished creating notification deliveries for matched rules",
            component="notifications",
            created_count=len(created_ids),
            correlation_id=correlation_id,
        )

        return created_ids

    def _get_default_recipients(self, channel: NotificationChannel) -> List[str]:
        """
        Returns default recipients for a channel.
        TODO: move to DB/config.
        """
        defaults = {
            NotificationChannel.EMAIL: ["fraud-alerts@company.com"],
            NotificationChannel.TELEGRAM: ["-1001234567890"],
        }
        return defaults.get(channel, [])

    async def _create_and_schedule_delivery(
        self, payload: NotificationDeliveryCreate, created_ids: List[UUID]
    ) -> Optional[UUID]:
        """
        Create a delivery record via repository, append its id to created_ids
        and schedule the asynchronous send task. Returns the delivery id on
        success or None on failure.
        """
        try:
            delivery = await self.repo.create_delivery(payload)
            created_ids.append(delivery.id)
            asyncio.create_task(self._send_notification_async(delivery.id))
            return delivery.id
        except Exception:
            logger.exception(
                "Failed to create/send delivery",
                component="notifications",
                metadata=getattr(payload, "metadata", {}),
            )
            increment_error_counter("delivery_create_error")
            return None

    async def _render_template(
        self,
        template: NotificationTemplate,
        transaction_data: Dict[str, Any],
        evaluation_result: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Render subject and body for a template.

        Uses a simple substitution scheme supporting both "{{var}}" and "{var}".
        Complex templates should be migrated to Jinja2 later.
        """
        try:
            vars_map = self._prepare_template_variables(
                template, transaction_data, evaluation_result
            )
            subject = None
            if getattr(template, "subject_template", None):
                subject = self._render_template_string(
                    template.subject_template, vars_map
                )
            body = self._render_template_string(template.body_template, vars_map)
            return {"subject": subject, "body": body}
        except Exception as exc:
            logger.exception(
                "Template rendering failed",
                component="notifications",
                template_id=str(getattr(template, "id", "unknown")),
            )
            raise NotificationError("template_render_failed") from exc

    def _prepare_template_variables(
        self,
        template: NotificationTemplate,
        transaction_data: Dict[str, Any],
        evaluation_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build variables dictionary according to template flags and input data.
        """
        variables: Dict[str, Any] = {}

        if getattr(template, "include_transaction_id", False):
            variables["transaction_id"] = transaction_data.get("id", "Unknown")

        if getattr(template, "include_amount", False):
            variables["amount"] = transaction_data.get("amount", 0)
            variables["currency"] = transaction_data.get("currency", "USD")

        if getattr(template, "include_timestamp", False):
            ts = transaction_data.get("timestamp")
            if isinstance(ts, str):
                variables["timestamp"] = ts
            elif ts:
                try:
                    variables["timestamp"] = ts.strftime("%Y-%m-%d %H:%M:%S UTC")
                except Exception:
                    variables["timestamp"] = str(ts)
            else:
                variables["timestamp"] = "Unknown"

        if getattr(template, "include_from_account", False):
            variables["from_account"] = transaction_data.get("from_account", "Unknown")

        if getattr(template, "include_to_account", False):
            variables["to_account"] = transaction_data.get("to_account", "Unknown")

        if getattr(template, "include_location", False):
            variables["location"] = transaction_data.get("location", "Unknown")

        if getattr(template, "include_device_info", False):
            variables["device_id"] = transaction_data.get("device_id", "Unknown")
            variables["ip_address"] = transaction_data.get("ip_address", "Unknown")

        if getattr(template, "include_triggered_rules", False):
            rule_results = evaluation_result.get("rule_results", []) or []
            triggered = [
                f"{r.get('rule_name', 'Unknown')} ({r.get('risk_level', 'Unknown')})"
                for r in rule_results
                if r.get("match_status") == "MATCHED"
            ]
            variables["triggered_rules"] = ", ".join(triggered) if triggered else "None"
            variables["triggered_rules_count"] = len(triggered)

        if getattr(template, "include_fraud_probability", False):
            rule_results = evaluation_result.get("rule_results", []) or []
            if rule_results:
                avg_conf = sum(
                    r.get("confidence_score", 0) for r in rule_results
                ) / len(rule_results)
                variables["fraud_probability"] = f"{avg_conf:.2%}"
            else:
                variables["fraud_probability"] = "Unknown"

        variables["overall_risk_level"] = evaluation_result.get(
            "overall_risk_level", "Unknown"
        )
        variables["flagged"] = evaluation_result.get("flagged", False)
        variables["should_block"] = evaluation_result.get("should_block", False)

        # merge custom_fields if present and is a dict
        try:
            custom = getattr(template, "custom_fields", {}) or {}
            if isinstance(custom, dict):
                variables.update(custom)
        except Exception:
            logger.warning(
                "Malformed custom_fields on template",
                template_id=str(getattr(template, "id", "unknown")),
            )

        return variables

    def _render_template_string(
        self, template_string: str, variables: Dict[str, Any]
    ) -> str:
        """
        Render a template string using simple replacement:
        converts '{{var}}' to '{var}' and uses str.format.
        Missing keys fall back to original template to avoid crashes.
        """
        try:
            safe = template_string.replace("{{", "{").replace("}}", "}")
            return safe.format(**variables)
        except KeyError as exc:
            logger.warning(
                "Missing template variable", component="notifications", detail=str(exc)
            )
            return template_string
        except Exception:
            logger.exception(
                "Unexpected template rendering error", component="notifications"
            )
            return template_string

    async def _send_notification_async(self, delivery_id: UUID) -> None:
        """
        Perform actual send for a delivery, persist attempt and update status.

        Fault-tolerant: any exception is recorded and converted into a recorded failed attempt.
        """
        try:
            delivery = await self.repo.get_delivery(delivery_id)
            if not delivery:
                logger.warning(
                    "Delivery not found",
                    component="notifications",
                    delivery_id=str(delivery_id),
                )
                return

            attempt_no = (delivery.attempts or 0) + 1

            channel_cfg = await self.repo.get_channel_config(delivery.channel)
            if not channel_cfg:
                err = "channel_configuration_missing"
                await self.repo.create_delivery_attempt(
                    delivery_id=delivery_id,
                    attempt_number=attempt_no,
                    success=False,
                    error_message=err,
                )
                await self.repo.update_delivery_status(
                    delivery_id, NotificationStatus.FAILED, error_message=err
                )
                logger.error(
                    "Missing channel configuration",
                    component="notifications",
                    delivery_id=str(delivery_id),
                )
                increment_error_counter("channel_config_missing")
                return

            send_ok = False
            send_err: Optional[str] = None

            try:
                if delivery.channel == NotificationChannel.EMAIL:
                    cfg = channel_cfg.config or {}
                    send_ok, send_err = await self.email_sender.send(
                        recipients=delivery.recipients,
                        message=delivery.body,
                        config=cfg,
                        subject=delivery.subject,
                    )
                elif delivery.channel == NotificationChannel.TELEGRAM:
                    cfg = channel_cfg.config or {}
                    send_ok, send_err = await self.telegram_sender.send(
                        recipients=delivery.recipients,
                        message=delivery.body,
                        config=cfg,
                    )
                else:
                    send_ok = False
                    send_err = f"unsupported_channel:{delivery.channel}"
            except Exception as exc:
                send_ok = False
                send_err = str(exc)

            # persist attempt
            try:
                await self.repo.create_delivery_attempt(
                    delivery_id=delivery_id,
                    attempt_number=attempt_no,
                    success=send_ok,
                    error_message=send_err,
                    metadata={"channel": str(delivery.channel)},
                )
                await self.repo.increment_delivery_attempt(delivery_id)
            except Exception:
                logger.exception(
                    "Failed to persist delivery attempt", delivery_id=str(delivery_id)
                )

            # update status based on result and attempts
            try:
                updated = await self.repo.get_delivery(delivery_id)
                if not updated:
                    logger.error(
                        "Delivery not found after send",
                        delivery_id=str(delivery_id),
                    )
                    return

                attempts_now = updated.attempts or attempt_no
                max_attempts = updated.max_attempts or 1

                if send_ok:
                    await self.repo.update_delivery_status(
                        delivery_id, NotificationStatus.DELIVERED
                    )
                    logger.info(
                        "Delivery delivered",
                        component="notifications",
                        delivery_id=str(delivery_id),
                    )
                else:
                    new_status = (
                        NotificationStatus.FAILED
                        if attempts_now >= max_attempts
                        else NotificationStatus.RETRYING
                    )
                    await self.repo.update_delivery_status(
                        delivery_id, new_status, error_message=send_err
                    )
                    logger.warning(
                        "Delivery send failed",
                        component="notifications",
                        delivery_id=str(delivery_id),
                        attempts=attempts_now,
                        max_attempts=max_attempts,
                        error=send_err,
                    )
                    increment_error_counter("delivery_send_error")
            except Exception:
                logger.exception(
                    "Failed to update delivery status", delivery_id=str(delivery_id)
                )
                increment_error_counter("delivery_update_error")

        except Exception:
            logger.exception(
                "Unexpected error in _send_notification_async",
                component="notifications",
                delivery_id=str(delivery_id),
            )
            increment_error_counter("notification_unexpected_error")
