import os
from email.message import EmailMessage

import aiosmtplib


async def send_activation_email(
    to_email: str,
    username: str,
    password: str,
    activation_link: str,
):
    message = EmailMessage()
    message["From"] = os.getenv("SMTP_FROM")
    message["To"] = to_email
    message["Subject"] = "Aktywacja konta"

    message.set_content(f"""
        Czesc,

        utworzono dla Ciebie konto w systemie inwentaryzacji.

        Login: {username}
        Haslo: {password}

        Kliknij link, aby aktywowac konto:
        {activation_link}

        Link jest wazny 24 godziny.""")

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_host:
        raise RuntimeError("SMTP_HOST is not set")

    await aiosmtplib.send(
        message,
        hostname=os.getenv("SMTP_HOST"),
        port=int(os.getenv("SMTP_PORT", "587")),
        username=os.getenv("SMTP_USER"),
        password=os.getenv("SMTP_PASSWORD"),
        start_tls=True,
    )

