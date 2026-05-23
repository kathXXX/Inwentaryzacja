import os
from email.message import EmailMessage

import aiosmtplib


async def send_activation_email(
    to_email: str,
    username: str,
    password: str,
    activation_link: str,
):
    print("Wysylam mail do:", to_email)

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
    if not smtp_user:
        raise RuntimeError("SMTP_USER is not set")
    if not smtp_password:
        raise RuntimeError("SMTP_PASSWORD is not set")

    print("Lacze z SMTP...")

    await aiosmtplib.send(
        message,
        hostname=smtp_host,
        port=smtp_port,
        username=smtp_user,
        password=smtp_password,
        use_tls=True,
    )

    print("Mail wyslany")

