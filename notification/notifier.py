import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from memory import db


def get_config():
    return {
        "email_enabled": os.getenv("NOTIFY_EMAIL", "").lower() == "true",
        "email_from": os.getenv("EMAIL_FROM", ""),
        "email_to": os.getenv("EMAIL_TO", ""),
        "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "smtp_user": os.getenv("SMTP_USER", ""),
        "smtp_pass": os.getenv("SMTP_PASS", ""),
        "wa_enabled": os.getenv("NOTIFY_WHATSAPP", "").lower() == "true",
        "wa_phone": os.getenv("WHATSAPP_PHONE", ""),
    }


def send_email(subject: str, body: str) -> str:
    cfg = get_config()
    if not cfg["email_enabled"] or not cfg["smtp_user"]:
        return "Email not configured"
    try:
        msg = MIMEMultipart()
        msg["From"] = cfg["email_from"] or cfg["smtp_user"]
        msg["To"] = cfg["email_to"] or cfg["smtp_user"]
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as server:
            server.starttls()
            server.login(cfg["smtp_user"], cfg["smtp_pass"])
            server.send_message(msg)
        return "Email sent"
    except Exception as e:
        return f"Email failed: {e}"


def send_whatsapp(message: str) -> str:
    cfg = get_config()
    if not cfg["wa_enabled"] or not cfg["wa_phone"]:
        return "WhatsApp not configured"
    try:
        import pywhatkit
        phone = cfg["wa_phone"]
        if not phone.startswith("+"):
            phone = "+91" + phone
        pywhatkit.sendwhatmsg_instantly(phone, message, wait_time=15, tab_close=True)
        return "WhatsApp sent"
    except Exception as e:
        return f"WhatsApp failed: {e}"


def get_tasks_due_soon() -> list[dict]:
    today = datetime.now().date()
    tasks = db.list_tasks("pending")
    alerts = []
    for t in tasks:
        if not t["deadline"]:
            continue
        try:
            due = datetime.strptime(t["deadline"], "%Y-%m-%d").date()
            diff = (due - today).days
            if diff < 0:
                alerts.append({"task": t, "type": "overdue", "days": -diff})
            elif diff == 0:
                alerts.append({"task": t, "type": "due_today", "days": 0})
            elif diff <= 2:
                alerts.append({"task": t, "type": "upcoming", "days": diff})
        except ValueError:
            continue
    return alerts


def check_and_notify() -> list[dict]:
    alerts = get_tasks_due_soon()
    results = []
    for a in alerts:
        t = a["task"]
        if a["type"] == "overdue":
            msg = f"OVERDUE: {t['title']} is {a['days']} day(s) overdue!"
        elif a["type"] == "due_today":
            msg = f"DUE TODAY: {t['title']} is due today!"
        else:
            msg = f"UPCOMING: {t['title']} is due in {a['days']} day(s)"

        results.append({"task": t["title"], "message": msg})

        email_r = send_email("Buddy Task Alert", msg)
        wa_r = send_whatsapp(msg)

        if "sent" in email_r or "sent" in wa_r:
            print(f"Notification sent for: {t['title']}")
    return results