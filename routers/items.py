import io
import os
import secrets
from urllib.parse import urlencode

import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session

import models
from database import db_dependency
from models import ItemStatus
from schemas import ItemBulkCreate, ItemCreate, ItemQrRead, ItemRead
from security import require_admin


router = APIRouter(prefix="/items", tags=["Przedmioty"])


def generate_qr_code() -> str:
    return secrets.token_urlsafe(18)


def generate_unique_qr_code(db: Session) -> str:
    while True:
        qr_code = generate_qr_code()
        exists = db.query(models.Item).filter(models.Item.qr_code == qr_code).first()
        if not exists:
            return qr_code


def get_public_frontend_url() -> str:
    return os.getenv(
        "PUBLIC_FRONTEND_URL",
        "https://web-production-53ca6.up.railway.app",
    ).rstrip("/")


def build_qr_target_url(qr_code: str) -> str:
    return f"{get_public_frontend_url()}/?{urlencode({'qr': qr_code})}"


def mm_to_px(mm: float, dpi: int) -> int:
    return int(mm / 25.4 * dpi)


def load_label_font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]

    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            pass

    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]

    for word in words[1:]:
        candidate = f"{current} {word}"
        if text_width(draw, candidate, font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break

    if len(lines) < max_lines:
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]

    if len(lines) == max_lines and text_width(draw, lines[-1], font) > max_width:
        line = lines[-1]
        while line and text_width(draw, f"{line}...", font) > max_width:
            line = line[:-1]
        lines[-1] = f"{line}..."

    return lines


def build_qr_label_pdf(items: list[models.Item]) -> io.BytesIO:
    dpi = int(os.getenv("QR_LABEL_DPI", "300"))
    width_mm = float(os.getenv("QR_LABEL_WIDTH_MM", "62"))
    height_mm = float(os.getenv("QR_LABEL_HEIGHT_MM", "29"))

    width = mm_to_px(width_mm, dpi)
    height = mm_to_px(height_mm, dpi)
    margin = mm_to_px(2, dpi)
    gap = mm_to_px(2, dpi)
    qr_size = min(height - 2 * margin, int(width * 0.42))

    title_font = load_label_font(max(18, int(height * 0.105)), bold=True)
    meta_font = load_label_font(max(13, int(height * 0.065)))
    small_font = load_label_font(max(10, int(height * 0.05)))

    pages: list[Image.Image] = []

    for item in items:
        page = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(page)

        qr_img = qrcode.make(build_qr_target_url(item.qr_code)).convert("RGB")
        qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.NEAREST)
        qr_x = margin
        qr_y = int((height - qr_size) / 2)
        page.paste(qr_img, (qr_x, qr_y))

        text_x = qr_x + qr_size + gap
        text_width_px = width - text_x - margin
        y = margin

        title_size = getattr(title_font, "size", max(18, int(height * 0.105)))
        meta_size = getattr(meta_font, "size", max(13, int(height * 0.065)))
        small_size = getattr(small_font, "size", max(10, int(height * 0.05)))

        for line in wrap_text(draw, item.nazwa, title_font, text_width_px, max_lines=2):
            draw.text((text_x, y), line, fill="black", font=title_font)
            y += int(title_size * 1.18)

        y += mm_to_px(1, dpi)
        meta_lines = [
            f"Sala: {item.lokalizacja}",
            f"Kat.: {item.kategoria}",
            f"ID: {item.id}",
        ]

        for line in meta_lines:
            for wrapped in wrap_text(draw, line, meta_font, text_width_px, max_lines=1):
                draw.text((text_x, y), wrapped, fill="black", font=meta_font)
                y += int(meta_size * 1.25)

        code_text = item.qr_code[:18]
        draw.text((text_x, height - margin - small_size), code_text, fill="black", font=small_font)
        pages.append(page)

    buf = io.BytesIO()
    first, rest = pages[0], pages[1:]
    first.save(buf, format="PDF", save_all=True, append_images=rest, resolution=dpi)
    buf.seek(0)
    return buf


def create_item_with_loan(db: Session, item_data: ItemCreate) -> models.Item:
    db_item = models.Item(**item_data.model_dump(), qr_code=generate_unique_qr_code(db))
    db.add(db_item)
    db.flush()

    db_loan = models.Loan(item_id=db_item.id, status=ItemStatus.dostepny, user_id=None)
    db.add(db_loan)
    return db_item


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ItemRead,
    summary="Dodaj przedmiot [administrator]",
)
async def create_item(
    item: ItemCreate,
    db: db_dependency,
    current_user: models.User = Depends(require_admin),
):
    db_item = create_item_with_loan(db, item)
    db.commit()
    db.refresh(db_item)

    return db_item


@router.post(
    "/bulk/pdf",
    summary="Dodaj wiele przedmiotow i pobierz PDF z QR [administrator]",
)
async def create_items_bulk_pdf(
    payload: ItemBulkCreate,
    db: db_dependency,
    current_user: models.User = Depends(require_admin),
):
    names = [name.strip() for name in payload.names if name.strip()]
    if not names:
        raise HTTPException(status_code=400, detail="Podaj przynajmniej jedna nazwe przedmiotu")

    items: list[models.Item] = []
    try:
        for name in names:
            item = create_item_with_loan(
                db,
                ItemCreate(
                    nazwa=name,
                    kategoria=payload.kategoria.strip(),
                    lokalizacja=payload.lokalizacja.strip(),
                ),
            )
            items.append(item)

        db.commit()
        for item in items:
            db.refresh(item)
    except Exception:
        db.rollback()
        raise

    pdf = build_qr_label_pdf(items)
    filename = "etykiety-qr.pdf"

    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/", response_model=list[ItemRead], summary="Lista wszystkich przedmiotow")
async def list_items(db: db_dependency):
    return db.query(models.Item).all()


@router.get(
    "/qr/{qr_code}",
    response_model=ItemQrRead,
    summary="Znajdz przedmiot po kodzie QR",
)
async def read_item_by_qr(qr_code: str, db: db_dependency):
    item = db.query(models.Item).filter(models.Item.qr_code == qr_code).first()
    if not item:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")

    loan = item.loan
    if not loan:
        raise HTTPException(status_code=404, detail="Brak rekordu dostepnosci dla tego przedmiotu")

    return ItemQrRead(
        item_id=item.id,
        nazwa=item.nazwa,
        kategoria=item.kategoria,
        lokalizacja=item.lokalizacja,
        qr_code=item.qr_code,
        loan_id=loan.id,
        status=loan.status,
    )


@router.get("/{item_id}/qr")
def generate_qr(item_id: int, db: db_dependency):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")

    data = build_qr_target_url(item.qr_code)

    qr = qrcode.make(data)

    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


@router.get("/{item_id}", response_model=ItemRead, summary="Pobierz przedmiot")
async def read_item(item_id: int, db: db_dependency):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")
    return item


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Usun przedmiot [administrator]",
)
async def delete_item(
    item_id: int,
    db: db_dependency,
    current_user: models.User = Depends(require_admin),
):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")

    db_loan = db.query(models.Loan).filter(models.Loan.item_id == item_id).first()
    if db_loan:
        db.delete(db_loan)

    db.delete(db_item)
    db.commit()
