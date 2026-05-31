import os
import resend


def is_email_dev_mode() -> bool:
    return os.getenv("EMAIL_DEV_MODE", "").lower() in {"1", "true", "yes", "on"}


async def send_email(to_email: str, subject: str, text: str):
    if not to_email:
        raise ValueError("Adres email jest wymagany")

    if is_email_dev_mode():
        print(f"[EMAIL_DEV_MODE] To: {to_email}\nSubject: {subject}\n{text}")
        return

    resend.api_key = os.getenv("RESEND_API_KEY")

    if not resend.api_key:
        raise RuntimeError("RESEND_API_KEY is not set")

    resend.Emails.send({
        "from": os.getenv("SMTP_FROM", "onboarding@resend.dev"),
        "to": to_email,
        "subject": subject,
        "text": text,
    })


async def send_activation_email(
    to_email: str,
    username: str,
    password: str,
    activation_link: str,
):
    await send_email(
        to_email,
        "Aktywacja konta",
        f"""
Czesc,

utworzono dla Ciebie konto w systemie inwentaryzacji.

Login: {username}
Haslo: {password}

Kliknij link, aby aktywowac konto:
{activation_link}

Link jest wazny 24 godziny.
"""
    )


async def send_login_code_email(to_email: str, code: str):
    await send_email(
        to_email,
        "Kod logowania do systemu inwentaryzacji",
        f"""
Czesc,

Twoj kod logowania to: {code}

Kod jest wazny przez 10 minut. Jesli to nie Ty probujesz sie zalogowac, zignoruj te wiadomosc.
"""
    )


async def send_loan_approved_email(
    to_email: str,
    user_name: str,
    item_name: str,
):
    await send_email(
        to_email,
        "Wypozyczenie zostalo zaakceptowane",
        f"""
Czesc {user_name},

Twoje wypozyczenie sprzetu "{item_name}" zostalo zaakceptowane.

Mozesz odebrac sprzet zgodnie z ustaleniami w systemie inwentaryzacji.
"""
    )

