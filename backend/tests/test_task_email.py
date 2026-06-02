import logging

from app.services import task_email


def test_send_task_assignment_email_skips_when_disabled(monkeypatch):
    monkeypatch.setattr(task_email.settings, "task_email_enabled", False)

    result = task_email.send_task_assignment_email(
        to_email="ravi@example.com",
        assignee_name="Ravi",
        task={"title": "Send notes"},
        meeting={"subject": "Roadmap sync"},
    )

    assert result.sent is False
    assert result.reason == "disabled"


def test_send_task_assignment_email_skips_missing_recipient(monkeypatch):
    monkeypatch.setattr(task_email.settings, "task_email_enabled", True)

    result = task_email.send_task_assignment_email(
        to_email=None,
        assignee_name="Ravi",
        task={"title": "Send notes"},
        meeting={"subject": "Roadmap sync"},
    )

    assert result.sent is False
    assert result.reason == "missing_recipient"


def test_send_task_assignment_email_sends_with_smtp(monkeypatch, caplog):
    sent_messages = []

    class FakeSMTP:
        def __init__(self, host, port):
            self.host = host
            self.port = port
            self.started_tls = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def starttls(self):
            self.started_tls = True

        def login(self, username, password):
            self.username = username
            self.password = password

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setattr(task_email.settings, "task_email_enabled", True)
    monkeypatch.setattr(task_email.settings, "task_smtp_host", "smtp.example.com")
    monkeypatch.setattr(task_email.settings, "task_smtp_port", 587)
    monkeypatch.setattr(task_email.settings, "task_smtp_username", "sender@example.com")
    monkeypatch.setattr(task_email.settings, "task_smtp_password", "secret")
    monkeypatch.setattr(task_email.settings, "task_smtp_from_address", "sender@example.com")
    monkeypatch.setattr(task_email.settings, "task_smtp_from_name", "MeetIQ")
    monkeypatch.setattr(task_email.settings, "task_smtp_enable_tls", True)
    monkeypatch.setattr(task_email.smtplib, "SMTP", FakeSMTP)

    caplog.set_level(logging.INFO, logger=task_email.__name__)

    result = task_email.send_task_assignment_email(
        to_email="ravi@example.com",
        assignee_name="Ravi",
        task={"title": "Send notes", "description": "Send the meeting notes."},
        meeting={"subject": "Roadmap sync"},
    )

    assert result.sent is True
    assert result.reason == "sent"
    assert sent_messages[0]["To"] == "ravi@example.com"
    assert sent_messages[0]["Subject"] == "New task assigned: Send notes"
    assert sent_messages[0].get_content_type() == "text/html"
    assert not sent_messages[0].is_multipart()
    assert "Send the meeting notes." in sent_messages[0].get_content()
    assert "password_length=6" in caplog.text
    assert f"password_sha256={task_email._safe_fingerprint('secret')}" in caplog.text
    assert "secret" not in caplog.text
