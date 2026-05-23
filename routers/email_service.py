import os
import resend


async def send_activation_email(
    to_email: str,
    username: str,
    password: str,
    activation_link: str,
):
    resend.api_key = os.getenv("RESEND_API_KEY")

    if not resend.api_key:
        raise RuntimeError("RESEND_API_KEY is not set")

    resend.Emails.send({
        "from": os.getenv("SMTP_FROM", "onboarding@resend.dev"),
        "to": to_email,
        "subject": "Aktywacja konta",
        "text": f"""
Czesc,

utworzono dla Ciebie konto w systemie inwentaryzacji.

Login: {username}
Haslo: {password}

Kliknij link, aby aktywowac konto:
{activation_link}

Link jest wazny 24 godziny.
"""
    })
    print("Mail wyslany")

