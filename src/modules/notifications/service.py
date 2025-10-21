"""
Notification service for sending alerts through email and Telegram.

This module renders templates, sends notifications via email and Telegram,
persists deliveries and attempts via the repository and logs all actions.

Notes:
- Metrics hooks are present as function calls; integrate Prometheus in reporting later.
- All network calls use httpx (async). Email uses smtplib executed in a threadpool to avoid blocking.
- Errors use core.exceptions.NotificationError where appropriate.
"""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from uuid import UUID

import httpx

if TYPE_CHECKING:
    # Imported for type checking only; runtime uses a session from the app
    from sqlalchemy.ext.asyncio import AsyncSession  # pragma: no cover
else:
    AsyncSession = Any

from src.core.exceptions import NotificationError
from src.core.logging import get_logger
from src.modules.notifications.enums import (
    NotificationChannel,
    NotificationStatus,
    TemplateType,
)
from src.modules.notifications.models import (
    NotificationTemplate,
)
from src.modules.notifications.repository import NotificationRepository
from src.modules.notifications.schemas import NotificationDeliveryCreate
from src.modules.reporting.metrics import (
    increment_error_counter,
    observe_notification_time,
)

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

    async def send_fraud_alert(
        self,
        transaction_data: Dict[str, Any],
        evaluation_result: Dict[str, Any],
        correlation_id: str,
    ) -> List[UUID]:
        """
        Create deliveries for enabled FRAUD_ALERT templates and trigger async sends.

        Returns list of created delivery IDs. This function is tolerant to errors:
        failures are logged and recorded via metrics but do not raise.
        """
        start = datetime.utcnow()
        try:
            templates = await self.repo.get_templates(
                template_type=TemplateType.FRAUD_ALERT, enabled_only=True
            )
        except Exception:
            logger.exception(
                "Failed to load templates",
                component="notifications",
                correlation_id=correlation_id,
            )
            increment_error_counter("templates_load_error")
            return []

        if not templates:
            logger.warning(
                "No enabled fraud templates found",
                component="notifications",
                correlation_id=correlation_id,
            )
            return []

        created_ids: List[UUID] = []

        for template in templates:
            try:
                if template.channel not in (
                    NotificationChannel.EMAIL,
                    NotificationChannel.TELEGRAM,
                ):
                    logger.info(
                        "Skipping unsupported template channel",
                        component="notifications",
                        event="unsupported_channel",
                        template_id=str(template.id),
                        channel=str(template.channel),
                        correlation_id=correlation_id,
                    )
                    # track usage even if skipped
                    try:
                        await self.repo.increment_template_usage(template.id)
                    except Exception:
                        logger.debug(
                            "Failed to increment template usage",
                            template_id=str(template.id),
                        )
                    continue

                rendered = await self._render_template(
                    template, transaction_data, evaluation_result
                )

                delivery_payload = NotificationDeliveryCreate(
                    transaction_id=UUID(transaction_data["id"]),
                    template_id=template.id,
                    channel=template.channel,
                    subject=rendered.get("subject"),
                    body=rendered["body"],
                    recipients=self._get_default_recipients(template.channel),
                    priority=template.priority,
                    scheduled_at=None,
                    metadata={
                        "correlation_id": correlation_id,
                        "template_name": template.name,
                        "rendered_at": datetime.utcnow().isoformat(),
                    },
                )

                delivery_record = await self.repo.create_delivery(delivery_payload)
                created_ids.append(delivery_record.id)

                # Best-effort increment usage
                try:
                    await self.repo.increment_template_usage(template.id)
                except Exception:
                    logger.debug(
                        "Failed to increment template usage",
                        template_id=str(template.id),
                    )

                # Fire-and-forget send
                asyncio.create_task(self._send_notification_async(delivery_record.id))

            except Exception:
                logger.exception(
                    "Failed to create notification delivery",
                    component="notifications",
                    template_id=str(getattr(template, "id", "unknown")),
                    correlation_id=correlation_id,
                )
                increment_error_counter("delivery_create_error")
                # continue processing other templates

        duration = (datetime.utcnow() - start).total_seconds()
        # TODO: expose this to Prometheus via reporting module
        observe_notification_time(duration)

        logger.info(
            "Finished creating notification deliveries",
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
                    send_ok, send_err = await self.send_email(
                        delivery.recipients, delivery.subject or "", delivery.body, cfg
                    )
                elif delivery.channel == NotificationChannel.TELEGRAM:
                    cfg = channel_cfg.config or {}
                    send_ok, send_err = await self.send_telegram(
                        delivery.recipients, delivery.body, cfg
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

    async def send_email(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        config: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Send email using smtplib executed in a threadpool to avoid blocking the event loop.

        Returns (success, error_message).
        """
        try:
            message = MIMEMultipart()
            message["From"] = config.get("username", "noreply@company.com")
            message["To"] = ", ".join(recipients)
            message["Subject"] = subject or ""
            message.attach(MIMEText(body or "", "plain"))

            loop = asyncio.get_running_loop()

            def _smtp_send() -> None:
                context = ssl.create_default_context()
                smtp_server = config["smtp_server"]
                smtp_port = config["smtp_port"]
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    if config.get("use_tls", True):
                        server.starttls(context=context)
                    if config.get("username") and config.get("password"):
                        server.login(config["username"], config["password"])
                    server.send_message(message)

            await loop.run_in_executor(None, _smtp_send)
            logger.info(
                "Email sent", component="notifications", recipients=len(recipients)
            )
            return True, None
        except Exception as exc:
            logger.exception("Email sending failed", component="notifications")
            return False, str(exc)

    async def send_telegram(
        self,
        recipients: List[str],
        message: str,
        config: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Send messages to Telegram chats using httpx AsyncClient.

        Returns (success, error_message). Partial failures are considered failures but recorded.
        """
        try:
            bot_token = config.get("bot_token")
            if not bot_token:
                return False, "bot_token_missing"

            success_count = 0
            async with httpx.AsyncClient(timeout=10.0) as client:
                for chat_id in recipients:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    payload = {
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": "HTML",
                    }
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        success_count += 1
                    else:
                        logger.warning(
                            "Telegram API returned non-200",
                            component="notifications",
                            chat_id=chat_id,
                            status_code=resp.status_code,
                            response=resp.text,
                        )

            if success_count == len(recipients):
                logger.info(
                    "Telegram messages sent",
                    component="notifications",
                    recipients=success_count,
                )
                return True, None
            err = f"telegram_partial:{success_count}/{len(recipients)}"
            logger.warning(err, component="notifications")
            return False, err
        except Exception as exc:
            logger.exception("Telegram sending failed", component="notifications")
            return False, str(exc)
