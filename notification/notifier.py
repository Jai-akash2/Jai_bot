import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv
from memory import db

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


INDIAN_SMS_GATEWAYS = [
    "airtelap.com", "jio.com", "jimsg.com",
    "vodafone.co.in", "bsnl.in", "sms.bsnl.in",
    "ideacellular.net",
]

def get_config():
    phone = os.getenv("SMS_PHONE", "")
    carrier = os.getenv("SMS_CARRIER", "").lower().strip()
    return {
        "email_enabled": os.getenv("NOTIFY_EMAIL", "").lower() == "true",
        "email_from": os.getenv("EMAIL_FROM", ""),
        "email_to": os.getenv("EMAIL_TO", ""),
        "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "smtp_user": os.getenv("SMTP_USER", ""),
        "smtp_pass": os.getenv("SMTP_PASS", ""),
        "sms_enabled": os.getenv("NOTIFY_SMS", "").lower() == "true",
        "sms_phone": phone,
        "sms_carrier": carrier,
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


def send_sms(message: str) -> str:
    cfg = get_config()
    if not cfg["sms_enabled"] or not cfg["sms_phone"]:
        return "SMS not configured"
    phone = cfg["sms_phone"].replace("+91", "").replace(" ", "")
    # Try Textbelt (free: 1 SMS/day)
    try:
        import httpx
        resp = httpx.post("https://textbelt.com/text", data={
            "phone": "91" + phone,
            "message": message[:160],
            "key": "textbelt",
        }, timeout=10)
        data = resp.json()
        if data.get("success"):
            return "SMS sent via Textbelt"
    except:
        pass
    # Fallback: try Indian carrier email gateways
    try:
        msg = MIMEText(message, "plain")
        msg["From"] = cfg["email_from"]
        msg["Subject"] = "Buddy Alert"
        with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"], timeout=8) as server:
            server.starttls()
            server.login(cfg["smtp_user"], cfg["smtp_pass"])
            for to_addr in [f"{phone}@{d}" for d in INDIAN_SMS_GATEWAYS]:
                try:
                    msg["To"] = to_addr
                    server.send_message(msg)
                except:
                    continue
        return "SMS sent via email gateway"
    except Exception as e:
        return f"SMS failed: {e}"


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
        sms_r = send_sms(msg)

        if "sent" in email_r or "sent" in sms_r:
            print(f"Notification sent for: {t['title']}")
    return results