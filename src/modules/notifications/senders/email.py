"""
Email notification sender using SMTP.

Sends email notifications using Python's built-in smtplib library.
Includes detailed documentation of the email sending workflow.
"""

import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

from src.core.logging import get_logger

from .base import BaseSender

logger = get_logger("notifications.email")


class EmailSender(BaseSender):
    """
    Email notification sender via SMTP.

    Sends emails using SMTP protocol. Executes blocking SMTP operations
    in a thread pool to avoid blocking the async event loop.

    EMAIL SENDING WORKFLOW:
    ========================

    1. PREPARATION PHASE
       - Validate configuration (SMTP server, port, credentials)
       - Create MIME message structure
       - Set email headers (From, To, Subject)
       - Attach message body (plain text or HTML)

    2. SMTP CONNECTION PHASE
       - Create SSL context for secure connection
       - Connect to SMTP server on specified port
       - Optionally upgrade to TLS (STARTTLS)

    3. AUTHENTICATION PHASE
       - Login to SMTP server with username/password
       - Handle authentication errors gracefully

    4. SENDING PHASE
       - Send the prepared MIME message
       - SMTP server processes and delivers email
       - Receive delivery confirmation or error

    5. CLEANUP PHASE
       - Close SMTP connection
       - Clean up resources
       - Log results

    SMTP PROTOCOL DETAILS:
    ======================
    - Port 25: Unencrypted (not recommended)
    - Port 465: SSL/TLS from start (implicit SSL)
    - Port 587: STARTTLS (explicit TLS upgrade) - RECOMMENDED

    Common SMTP Servers:
    - Gmail: smtp.gmail.com:587
    - Outlook: smtp-mail.outlook.com:587
    - SendGrid: smtp.sendgrid.net:587
    - Amazon SES: email-smtp.region.amazonaws.com:587
    """

    async def send(
        self,
        recipients: List[str],
        message: str,
        config: Dict[str, Any],
        subject: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Send email to recipients via SMTP.

        This method orchestrates the entire email sending process:
        1. Validates inputs and configuration
        2. Creates MIME message with proper headers
        3. Executes SMTP sending in thread pool (non-blocking)
        4. Handles errors and returns results

        Args:
            recipients: List of email addresses to send to
            message: Email body content (plain text)
            config: SMTP configuration dictionary:
                - smtp_server (str): SMTP server hostname
                - smtp_port (int): SMTP server port (usually 587)
                - use_tls (bool): Whether to use STARTTLS (recommended)
                - username (str): SMTP authentication username
                - password (str): SMTP authentication password
                - from_name (str, optional): Sender display name
            subject: Email subject line

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
            - (True, None) if email sent successfully
            - (False, error_description) if sending failed

        Example config:
            {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "use_tls": True,
                "username": "alerts@company.com",
                "password": "app-password",
                "from_name": "Fraud Detection System"
            }
        """
        if not recipients:
            return False, "no_recipients"

        if not subject:
            subject = "Notification"

        try:
            # Step 1: Prepare MIME message
            # -----------------------------
            # MIMEMultipart allows us to have multiple parts (text, HTML, attachments)
            # even though we're currently only using plain text
            mime_message = MIMEMultipart()

            # Set email headers
            # "From" header - can include display name: "Name <email@domain.com>"
            from_address = config.get("SMTP_HOST", "noreply@company.com")
            from_name = config.get("SMTP_USER", "")
            if from_name:
                mime_message["From"] = f"{from_name} <{from_address}>"
            else:
                mime_message["From"] = from_address

            # "To" header - comma-separated list of recipients
            mime_message["To"] = ", ".join(recipients)

            # "Subject" header
            mime_message["Subject"] = subject

            # Attach message body
            # MIMEText creates a MIME part with the content type "text/plain"
            # We could also use "text/html" for HTML emails
            text_part = MIMEText(message, "plain", "utf-8")
            mime_message.attach(text_part)

            # Step 2: Execute SMTP sending in thread pool
            # --------------------------------------------
            # SMTP operations are blocking I/O, so we run them in a separate thread
            # to avoid blocking the async event loop
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,  # Use default thread pool executor
                self._send_smtp_blocking,
                mime_message,
                config,
            )

            logger.info(
                "Email sent successfully",
                component="notifications",
                event="email_sent",
                recipients_count=len(recipients),
                recipients=recipients,
            )
            return True, None

        except smtplib.SMTPAuthenticationError as e:
            # Authentication failed - wrong username/password
            error_msg = f"smtp_auth_failed: {str(e)}"
            logger.error(
                "SMTP authentication failed",
                component="notifications",
                event="email_auth_failed",
                error=str(e),
            )
            return False, error_msg

        except smtplib.SMTPConnectError as e:
            # Cannot connect to SMTP server
            error_msg = f"smtp_connect_failed: {str(e)}"
            logger.error(
                "SMTP connection failed",
                component="notifications",
                event="email_connect_failed",
                smtp_server=config.get("smtp_server"),
                smtp_port=config.get("smtp_port"),
                error=str(e),
            )
            return False, error_msg

        except smtplib.SMTPException as e:
            # General SMTP error
            error_msg = f"smtp_error: {str(e)}"
            logger.error(
                "SMTP error",
                component="notifications",
                event="email_smtp_error",
                error=str(e),
            )
            return False, error_msg

        except Exception as e:
            # Unexpected error
            error_msg = f"email_unexpected_error: {str(e)}"
            logger.exception(
                f"Unexpected error sending email {e}",
                component="notifications",
                event="email_unexpected_error",
            )
            return False, error_msg

    def _send_smtp_blocking(
        self, mime_message: MIMEMultipart, config: Dict[str, Any]
    ) -> None:
        """
        Blocking SMTP send operation.

        This method runs in a thread pool to avoid blocking the event loop.
        It performs the actual SMTP communication.

        DETAILED SMTP WORKFLOW:
        =======================

        1. CREATE SSL CONTEXT
           - SSL context manages TLS/SSL settings
           - create_default_context() uses secure defaults:
             * Verifies server certificates
             * Uses strong cipher suites
             * Enforces TLS 1.2+ protocol

        2. CONNECT TO SMTP SERVER
           - Creates TCP connection to server
           - Does NOT use encryption yet (for port 587)

        3. UPGRADE TO TLS (if use_tls=True)
           - Sends STARTTLS command
           - Upgrades plain connection to encrypted TLS
           - All subsequent communication is encrypted
           - This prevents credentials from being sent in plaintext

        4. AUTHENTICATE
           - Sends LOGIN command with username/password
           - Credentials are encrypted if TLS is enabled
           - Server validates credentials

        5. SEND MESSAGE
           - Sends MAIL FROM command (sender)
           - Sends RCPT TO commands (recipients)
           - Sends DATA command (message content)
           - Server accepts and queues message for delivery

        6. DISCONNECT
           - Sends QUIT command
           - Closes TCP connection
           - Server finalizes delivery

        Args:
            mime_message: Prepared MIME message
            config: SMTP configuration

        Raises:
            smtplib.SMTPAuthenticationError: Authentication failed
            smtplib.SMTPConnectError: Connection failed
            smtplib.SMTPException: Other SMTP errors
        """
        # Extract configuration
        smtp_server = config["SMTP_HOST"]
        smtp_port = config["SMTP_PORT"]
        use_tls = config.get("USE_TLS", True)
        username = config.get("SMTP_USER")
        password = config.get("SMTP_PASSWORD")

        # Step 1: Create SSL context for secure communication
        # ----------------------------------------------------
        # This creates a context with secure default settings:
        # - Validates server certificates against CA bundle
        # - Uses strong cipher suites
        # - Enforces modern TLS versions (1.2+)
        ssl_context = ssl.create_default_context()

        # Step 2: Create SMTP connection
        # -------------------------------
        # Using context manager (with statement) ensures connection is closed
        # even if an error occurs
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            # Enable debug output to console (useful for troubleshooting)
            # server.set_debuglevel(1)

            # Step 3: Upgrade to TLS if configured
            # -------------------------------------
            if use_tls:
                # STARTTLS command:
                # - Tells server "I want to upgrade to TLS"
                # - Server responds with "ready to start TLS"
                # - TLS handshake occurs
                # - Connection is now encrypted
                server.starttls(context=ssl_context)

                # After STARTTLS, we need to identify ourselves again
                # Some servers require EHLO after STARTTLS
                server.ehlo()

            # Step 4: Authenticate with SMTP server
            # --------------------------------------
            if username and password:
                # LOGIN command with credentials
                # These are sent encrypted if TLS is enabled
                server.login(username, password)

            # Step 5: Send the email message
            # -------------------------------
            # send_message() handles:
            # - Extracting sender and recipients from MIME headers
            # - Sending MAIL FROM, RCPT TO, DATA commands
            # - Encoding message content
            # - Handling multipart messages
            server.send_message(mime_message)

        # Step 6: Connection automatically closed by context manager
        # -----------------------------------------------------------
        logger.debug(
            "SMTP send completed",
            component="notifications",
            event="smtp_completed",
            smtp_server=smtp_server,
        )

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate SMTP configuration.

        Checks that all required fields are present and valid.

        Args:
            config: Configuration to validate

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        required_fields = ["smtp_server", "smtp_port"]

        for field in required_fields:
            if field not in config:
                return False, f"Missing required field: {field}"

        # Validate port is integer
        try:
            port = int(config["smtp_port"])
            if port < 1 or port > 65535:
                return False, f"Invalid port number: {port}"
        except (ValueError, TypeError):
            return False, "smtp_port must be an integer"

        # Warn if no authentication configured
        if not config.get("username") or not config.get("password"):
            logger.warning(
                "SMTP configuration has no authentication",
                component="notifications",
                event="smtp_no_auth",
            )

        return True, None

    def get_channel_name(self) -> str:
        """
        Get channel name.

        Returns:
            "email"
        """
        return "email"
