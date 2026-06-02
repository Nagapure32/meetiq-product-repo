import hashlib
import html
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TaskEmailResult:
    sent: bool
    reason: str
    error: str | None = None


def send_task_assignment_email(
    to_email: str | None,
    assignee_name: str | None,
    task: dict[str, Any],
    meeting: dict[str, Any] | None,
) -> TaskEmailResult:
    if not settings.task_email_enabled:
        return TaskEmailResult(False, "disabled")
    if not to_email:
        return TaskEmailResult(False, "missing_recipient")
    if not _smtp_configured():
        return TaskEmailResult(False, "smtp_not_configured")

    message = EmailMessage()
    from_address = settings.task_smtp_from_address or settings.task_smtp_username
    message["From"] = f"{settings.task_smtp_from_name} <{from_address}>"
    message["To"] = to_email
    message["Subject"] = f"New task assigned: {task.get('title')}"
    message.set_content(_html_body(assignee_name, task, meeting), subtype="html")

    try:
        logger.warning(
            "Task email SMTP config: host=%s port=%s tls=%s username=%s from=%s "
            "password_length=%s password_sha256=%s",
            settings.task_smtp_host,
            settings.task_smtp_port,
            settings.task_smtp_enable_tls,
            settings.task_smtp_username,
            from_address,
            len(settings.task_smtp_password),
            _safe_fingerprint(settings.task_smtp_password),
        )
        with smtplib.SMTP(settings.task_smtp_host, settings.task_smtp_port) as smtp:
            if settings.task_smtp_enable_tls:
                smtp.starttls()
            smtp.login(settings.task_smtp_username, settings.task_smtp_password)
            smtp.send_message(message)
    except Exception as exc:
        return TaskEmailResult(False, "smtp_error", str(exc))

    return TaskEmailResult(True, "sent")


def _smtp_configured() -> bool:
    return all(
        [
            settings.task_smtp_host,
            settings.task_smtp_username,
            settings.task_smtp_password,
            settings.task_smtp_from_address or settings.task_smtp_username,
        ]
    )


def _safe_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _plain_body(
    assignee_name: str | None,
    task: dict[str, Any],
    meeting: dict[str, Any] | None,
) -> str:
    return (
        f"Hi {assignee_name or 'there'},\n\n"
        f"You have been assigned a task from {meeting_subject(meeting)}.\n\n"
        f"Task: {task.get('title')}\n"
        f"Description: {task.get('description') or 'No description'}\n"
        f"Priority: {task.get('priority') or 'medium'}\n"
        f"Due date: {task.get('due_date') or 'Not set'}\n"
    )


def _html_body(
    assignee_name: str | None,
    task: dict[str, Any],
    meeting: dict[str, Any] | None,
) -> str:
    return f"""
    <p>Hi {html.escape(assignee_name or 'there')},</p>
    <p>You have been assigned a task from
    <strong>{html.escape(meeting_subject(meeting))}</strong>.</p>
    <p><strong>Task:</strong> {html.escape(str(task.get('title') or 'Untitled task'))}<br>
    <strong>Description:</strong>
    {html.escape(str(task.get('description') or 'No description'))}<br>
    <strong>Priority:</strong> {html.escape(str(task.get('priority') or 'medium'))}<br>
    <strong>Due date:</strong> {html.escape(str(task.get('due_date') or 'Not set'))}</p>
    """


def meeting_subject(meeting: dict[str, Any] | None) -> str:
    return str((meeting or {}).get("subject") or "a meeting")
