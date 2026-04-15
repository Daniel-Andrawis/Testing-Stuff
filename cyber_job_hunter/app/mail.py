import resend

from app.config import RESEND_API_KEY, RESEND_FROM_EMAIL


def send_email(to: str, subject: str, html: str):
    if not RESEND_API_KEY:
        print(f"[mail] RESEND_API_KEY not set — would send to {to}: {subject}")
        return None

    resend.api_key = RESEND_API_KEY
    return resend.Emails.send({
        "from": RESEND_FROM_EMAIL,
        "to": [to],
        "subject": subject,
        "html": html,
    })
