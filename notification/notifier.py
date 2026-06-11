import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv
from memory import db

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def get_config():
    return {
        "email_enabled": os.getenv("NOTIFY_EMAIL", "").lower() == "true",
        "email_from": os.getenv("EMAIL_FROM", ""),
        "email_to": os.getenv("EMAIL_TO", ""),
        "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "smtp_user": os.getenv("SMTP_USER", ""),
        "smtp_pass": os.getenv("SMTP_PASS", ""),
        "whatsapp_enabled": bool(os.getenv("WHATSAPP_API_KEY")),
        "whatsapp_phone": os.getenv("WHATSAPP_PHONE", "").replace(" ", ""),
        "whatsapp_api_key": os.getenv("WHATSAPP_API_KEY", ""),
        "sms_enabled": os.getenv("NOTIFY_SMS", "").lower() == "true",
        "sms_phone": os.getenv("SMS_PHONE", ""),
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
        with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"], timeout=10) as server:
            server.starttls()
            server.login(cfg["smtp_user"], cfg["smtp_pass"])
            server.send_message(msg)
        return "Email sent"
    except Exception as e:
        return f"Email failed: {e}"


def send_whatsapp(message: str) -> str:
    cfg = get_config()
    if not cfg["whatsapp_enabled"]:
        return "WhatsApp not configured"
    import httpx
    try:
        resp = httpx.get("https://api.callmebot.com/whatsapp.php", params={
            "phone": cfg["whatsapp_phone"],
            "text": message[:160],
            "apikey": cfg["whatsapp_api_key"],
        }, timeout=10)
        if resp.status_code == 200 and "sent" in resp.text.lower():
            return "WhatsApp sent"
        return f"WhatsApp failed: {resp.text[:100]}"
    except Exception as e:
        return f"WhatsApp error: {e}"


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

        wa_r = send_whatsapp(msg)
        email_r = send_email("Buddy Task Alert", msg)

        if "sent" in wa_r or "sent" in email_r:
            print(f"Notification sent for: {t['title']} ({wa_r}, {email_r})")
    return results