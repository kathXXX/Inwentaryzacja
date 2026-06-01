from models import ItemStatus


def test_available_status_value():
    assert ItemStatus.dostepny.value == "dostepny"


def test_reserved_status_value():
    assert ItemStatus.zarezerwowany.value == "zarezerwowany"


def test_borrowed_status_value():
    assert ItemStatus.wypozyczony.value == "wypozyczony"


def test_available_not_reserved():
    assert ItemStatus.dostepny != ItemStatus.zarezerwowany


def test_available_not_borrowed():
    assert ItemStatus.dostepny != ItemStatus.wypozyczony


def test_reserved_not_borrowed():
    assert ItemStatus.zarezerwowany != ItemStatus.wypozyczony