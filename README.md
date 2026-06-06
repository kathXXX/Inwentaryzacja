# Inwentaryzacja
STRONA: https://www.inventory.edu.pl/


# System Inwentaryzacji i Wypożyczeń Sprzętu

Aplikacja webowa umożliwiająca zarządzanie sprzętem, użytkownikami oraz procesem wypożyczania wyposażenia uczelni lub instytucji.

## Funkcjonalności

### Użytkownicy

* rejestracja użytkowników przez administratora,
* aktywacja konta przez link wysłany e-mailem,
* logowanie loginem i hasłem,
* zmiana hasła,
* role użytkowników:

  * Student,
  * Nauczyciel,
  * Administrator.

### Sprzęt

* dodawanie przedmiotów,
* usuwanie przedmiotów,
* przeglądanie listy sprzętu,
* generowanie kodów QR,
* drukowanie etykiet QR,
* sprawdzanie dostępności sprzętu.

### Wypożyczenia

* składanie wniosków o wypożyczenie,
* zatwierdzanie wypożyczeń przez nauczyciela,
* bezpośrednie wypożyczanie przez nauczyciela,
* zwrot sprzętu,
* historia wypożyczeń.

### Bezpieczeństwo

* JWT Authentication,
* haszowanie haseł przy użyciu bcrypt,
* ograniczanie liczby żądań (Rate Limiting),
* autoryzacja oparta o role użytkowników.

---

## Technologie

### Backend

* Python 3.14
* FastAPI
* SQLAlchemy
* Pydantic
* JWT (python-jose)
* Passlib / bcrypt
* SlowAPI

### Frontend

* HTML
* CSS
* JavaScript

### Baza danych

* mySQL (Railway)

### Testy

* Pytest
* Pytest Asyncio
* Pytest Cov

---

## Instalacja

### Klonowanie repozytorium

```bash
git clone <adres_repozytorium>
cd Inwentaryzacja
```

### Instalacja zależności

```bash
pip install -r requirements.txt
```

---

## API:

```text
https://web-production-53ca6.up.railway.app/docs
```



## Testy

Uruchomienie testów:

```bash
pytest
```

Raport pokrycia kodu:

```bash
pytest --cov=. --cov-report=term-missing
```

Aktualne wyniki:

* 78 testów
* 78 testów zakończonych sukcesem
* 0 błędów
* 78% pokrycia kodu testami

Zakres testów:

* autoryzacja,
* bezpieczeństwo,
* modele danych,
* walidacja schematów,
* zarządzanie sprzętem,
* proces wypożyczeń,
* zarządzanie użytkownikami.


## Autorzy
Karolina Seta
Klaudia Pijanowska
Marek Wiśniewski
Łukasz Łazuga

Projekt wykonany w ramach pracy inżynierskiej / projektu uczelnianego.

