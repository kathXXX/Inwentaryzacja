from routers.items import (
    build_qr_target_url,
    generate_qr_code,
    mm_to_px,
)


def test_generate_qr_code_returns_string():
    code = generate_qr_code()

    assert isinstance(code, str)


def test_generate_qr_code_not_empty():
    code = generate_qr_code()

    assert len(code) > 10


def test_generate_qr_code_unique():
    code1 = generate_qr_code()
    code2 = generate_qr_code()

    assert code1 != code2


def test_mm_to_px_positive_value():
    result = mm_to_px(25.4, 300)

    assert result == 300


def test_mm_to_px_zero():
    assert mm_to_px(0, 300) == 0


def test_build_qr_target_url_contains_qr_parameter():
    url = build_qr_target_url("ABC123")

    assert "qr=ABC123" in url


def test_build_qr_target_url_returns_https_url():
    url = build_qr_target_url("ABC123")

    assert url.startswith("https://")


def test_build_qr_target_url_preserves_code():
    code = "test-code-123"

    url = build_qr_target_url(code)

    assert code in url