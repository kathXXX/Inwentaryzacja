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
        "from": os.getenv("SMTP_FROM", "noreply@inventory.edu.pl"),
        "to": to_email,
        "subject": subject,
        "text": text,
    })

async def send_password_reset_code_email(to_email: str, code: str):
    await send_email(
        to_email,
        "Kod resetowania hasla",
        f"""
Czesc,

Twoj kod resetowania hasla to: {code}

Kod jest wazny przez 10 minut. Jesli to nie Ty probujesz zresetowac haslo, zignoruj te wiadomosc.
"""
    )

async def send_activation_email(
    to_email: str,
    username: str,
    password: str,
    activation_code: str,
):
    await send_email(
        to_email,
        "Kod aktywacji konta",
        f"""
Czesc,

utworzono dla Ciebie konto w systemie inwentaryzacji.

Login: {username}
Haslo: {password}

Kod aktywacji konta: {activation_code}

Kod jest wazny 24 godziny. Wpisz go na stronie logowania, aby aktywowac konto.
"""
    )


async def send_loan_approved_email(
    to_email: str,
    user_name: str,
    item_name: str,
    starts_at: str | None = None,
    due_at: str | None = None,
):
    period_text = ""
    if starts_at or due_at:
        period_text = f"\nTermin wypozyczenia: {starts_at or '-'} - {due_at or '-'}\n"

    await send_email(
        to_email,
        "Wypozyczenie zostalo zaakceptowane",
        f"""
Czesc {user_name},

Twoje wypozyczenie sprzetu "{item_name}" zostalo zaakceptowane.
{period_text}

Mozesz odebrac sprzet zgodnie z ustaleniami w systemie inwentaryzacji.
"""
    )


async def send_loan_due_reminder_email(
    to_email: str,
    user_name: str,
    item_name: str,
    starts_at: str | None,
    due_at: str,
):
    await send_email(
        to_email,
        "Przypomnienie o zwrocie sprzetu",
        f"""
Czesc {user_name},

Przypominamy, ze sprzet "{item_name}" ma termin wypozyczenia: {starts_at or "-"} - {due_at}.

Ta wiadomosc jest wysylana tylko do studenta, ktory wypozyczyl sprzet.
"""
    )

