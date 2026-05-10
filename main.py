import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.middleware import SlowAPIMiddleware

from rate_limit import limiter
from routers import auth, availability, items, loans, users
from seed import seed_initial_admin


app = FastAPI()

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def api_prefix_compatibility(request: Request, call_next):
    path = request.scope.get("path", "")
    if path == "/api":
        request.scope["path"] = "/"
    elif path.startswith("/api/"):
        request.scope["path"] = path[4:]

    raw_path = request.scope.get("raw_path")
    if raw_path == b"/api":
        request.scope["raw_path"] = b"/"
    elif raw_path and raw_path.startswith(b"/api/"):
        request.scope["raw_path"] = raw_path[4:]

    return await call_next(request)


frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "https://web-production-53ca6.up.railway.app,http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(items.router)
app.include_router(availability.router)
app.include_router(loans.router)

seed_initial_admin()

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
