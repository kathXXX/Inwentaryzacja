from routers.auth import mask_email, generate_login_code


def test_mask_email_one_letter_local_part():
    assert mask_email("a@example.com") == "a***@example.com"


def test_mask_email_two_letters_local_part():
    assert mask_email("ab@example.com") == "a***@example.com"


def test_mask_email_long_local_part():
    assert mask_email("admin@example.com") == "a***n@example.com"


def test_mask_email_empty_string():
    assert mask_email("") == ""


def test_mask_email_missing_at_symbol():
    assert mask_email("admin.example.com") == "admin.example.com"


def test_generate_login_code_returns_string():
    code = generate_login_code()
    assert isinstance(code, str)


def test_generate_login_code_is_always_6_digits():
    for _ in range(100):
        code = generate_login_code()
        assert len(code) == 6
        assert code.isdigit()


def test_generate_login_code_can_start_with_zero():
    # Ten test sprawdza tylko, czy funkcja zachowuje format 000000-999999.
    # Nie wymuszamy faktycznego wylosowania zera na początku.
    code = generate_login_code()
    number = int(code)

    assert 0 <= number <= 999999
    assert code == f"{number:06d}"