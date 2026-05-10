# Inwentaryzacja

Aplikacja do inwentaryzacji i wypożyczania sprzętu.

## Obecny deployment na Railway

Railway uruchamia aplikację jako jeden proces FastAPI:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

To wynika z `Procfile`. W tym trybie backend serwuje też statyczny frontend z katalogu `frontend`.

Wymagane zmienne środowiskowe:

- `DATABASE_URL`
- `SECRET_KEY`

Opcjonalne zmienne:

- `FRONTEND_ORIGINS`
- `PUBLIC_FRONTEND_URL`
- `INITIAL_ADMIN_USERNAME`
- `INITIAL_ADMIN_PASSWORD`
- `INITIAL_ADMIN_FIRST_NAME`
- `INITIAL_ADMIN_LAST_NAME`

## Lokalnie przez Docker Compose

Nowy lokalny układ ma trzy kontenery:

- `frontend` - Nginx serwujący pliki z `frontend/`
- `backend` - FastAPI/Uvicorn
- `db` - MySQL 8.4

Uruchomienie:

```bash
docker compose up --build
```

Adresy:

- Frontend: http://localhost:8080
- Backend API: http://localhost:8000
- Dokumentacja API: http://localhost:8000/docs
- MySQL z hosta: `localhost:3307`

Domyślne lokalne konto administratora:

- login: `admin`
- hasło: `admin12345`

Frontend komunikuje się z backendem przez `/api`, a Nginx przekazuje te żądania do kontenera `backend`.

Wyczyszczenie lokalnej bazy:

```bash
docker compose down -v
```
