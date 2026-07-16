"""
services/smtp_service.py
=========================
Reusable SMTP email-sending functions. All email sending in the app
goes through this module so there is a single, well-tested code path
for constructing and sending messages.

Public functions:
    send_wish_email(name, phone, message) -> bool
    send_payment_success(name, phone, amount, reference) -> bool
    send_payment_failed(name, phone, amount, reference, reason) -> bool
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import Config
from utils.helpers import current_timestamp, format_currency
from utils.logger import get_logger

logger = get_logger(__name__)


def _send_email(subject: str, body: str, to_email: str | None = None) -> bool:
    """
    Core email-sending routine. Connects to the configured SMTP server,
    sends a single plaintext/HTML message, and reports success/failure.

    Returns True on success, False on any failure (never raises, so
    callers - typically request handlers - never crash because of an
    email delivery issue).
    """
    recipient = to_email or Config.RECIPIENT_EMAIL

    if not Config.SMTP_EMAIL or not Config.SMTP_PASSWORD or not recipient:
        logger.warning("SMTP not fully configured; skipping email send: %s", subject)
        return False

    message = MIMEMultipart("alternative")
    message["From"] = Config.SMTP_EMAIL
    message["To"] = recipient
    message["Subject"] = subject
    message.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(Config.SMTP_EMAIL, Config.SMTP_PASSWORD)
            server.sendmail(Config.SMTP_EMAIL, recipient, message.as_string())
        logger.info("Email sent successfully: %s -> %s", subject, recipient)
        return True
    except smtplib.SMTPException as exc:
        logger.error("SMTP error while sending '%s': %s", subject, exc)
        return False
    except Exception as exc:  # noqa: BLE001 - never let email failures crash the app
        logger.error("Unexpected error while sending '%s': %s", subject, exc)
        return False


def send_wish_email(name: str, phone: str, message: str) -> bool:
    """Send a notification email whenever a visitor submits a birthday wish."""
    subject = f"New Birthday Wish from {name}"
    body = f"""
    <h2>New Birthday Wish Received</h2>
    <p><strong>Name:</strong> {name}</p>
    <p><strong>Phone:</strong> {phone}</p>
    <p><strong>Message:</strong></p>
    <p>{message}</p>
    <hr>
    <p style="color:#888;font-size:12px;">Received at {current_timestamp()}</p>
    """
    return _send_email(subject, body)


def send_payment_success(name: str, phone: str, amount: float, reference: str) -> bool:
    """Send a confirmation email when a gift payment succeeds."""
    subject = f"Gift Payment Received - {reference}"
    body = f"""
    <h2>Birthday Gift Payment Successful</h2>
    <p><strong>From:</strong> {name or 'Anonymous'}</p>
    <p><strong>Phone:</strong> {phone}</p>
    <p><strong>Amount:</strong> {format_currency(amount)}</p>
    <p><strong>Reference:</strong> {reference}</p>
    <hr>
    <p style="color:#888;font-size:12px;">Confirmed at {current_timestamp()}</p>
    """
    return _send_email(subject, body)


def send_payment_failed(name: str, phone: str, amount: float, reference: str, reason: str = "Unknown") -> bool:
    """Send a notification email when a gift payment fails or is cancelled."""
    subject = f"Gift Payment Failed - {reference}"
    body = f"""
    <h2>Birthday Gift Payment Failed</h2>
    <p><strong>From:</strong> {name or 'Anonymous'}</p>
    <p><strong>Phone:</strong> {phone}</p>
    <p><strong>Amount:</strong> {format_currency(amount)}</p>
    <p><strong>Reference:</strong> {reference}</p>
    <p><strong>Reason:</strong> {reason}</p>
    <hr>
    <p style="color:#888;font-size:12px;">Recorded at {current_timestamp()}</p>
    """
    return _send_email(subject, body)
