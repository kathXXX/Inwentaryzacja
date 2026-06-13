from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Depends, HTTPException

import models
from database import db_dependency
from models import ItemStatus
from routers.location_service import ensure_item_location, item_location_name, normalize_location_name
from schemas import (
    InventoryCheckItem,
    LocationInventoryCheckRead,
    LocationInventoryCheckRequest,
    LocationRead,
    WrongLocationItem,
)
from security import require_teacher


router = APIRouter(prefix="/locations", tags=["Lokalizacje"])


def extract_qr_code(raw_value: str) -> str:
    value = (raw_value or "").strip()
    if not value:
        return ""

    parsed = urlparse(value)
    query = parse_qs(parsed.query)
    if query.get("qr"):
        return query["qr"][0]

    return value


def location_read(location: models.Location) -> LocationRead:
    return LocationRead(
        id=location.id,
        name=location.name,
        description=location.description,
        items_count=len(location.items),
    )


def inventory_item_read(item: models.Item, scanned: bool = False) -> InventoryCheckItem:
    loan = item.loan
    return InventoryCheckItem(
        item_id=item.id,
        nazwa=item.nazwa,
        kategoria=item.kategoria,
        lokalizacja=item_location_name(item),
        location_id=item.location_id,
        qr_code=item.qr_code,
        loan_id=loan.id if loan else None,
        status=loan.status if loan else ItemStatus.dostepny,
        user_id=loan.user_id if loan else None,
        starts_at=loan.starts_at if loan else None,
        due_at=loan.due_at if loan else None,
        scanned=scanned,
    )


def find_location(db, payload: LocationInventoryCheckRequest) -> models.Location:
    if payload.location_id:
        location = db.query(models.Location).filter(models.Location.id == payload.location_id).first()
    elif payload.location_name:
        name = normalize_location_name(payload.location_name)
        location = db.query(models.Location).filter(models.Location.name == name).first()
    else:
        raise HTTPException(status_code=400, detail="Podaj sale/lokalizacje")

    if not location:
        raise HTTPException(status_code=404, detail="Lokalizacja nie znaleziona")

    return location


@router.get("/", response_model=list[LocationRead], summary="Lista lokalizacji [nauczyciel/admin]")
async def list_locations(
    db: db_dependency,
    current_user: models.User = Depends(require_teacher),
):
    locations = db.query(models.Location).order_by(models.Location.name).all()
    return [location_read(location) for location in locations]


@router.post(
    "/inventory-check/",
    response_model=LocationInventoryCheckRead,
    summary="Sprawdz zeskanowane QR w konkretnej sali [nauczyciel/admin]",
)
async def inventory_check(
    payload: LocationInventoryCheckRequest,
    db: db_dependency,
    current_user: models.User = Depends(require_teacher),
):
    location = find_location(db, payload)

    # Podpinamy stare rekordy, ktore mialy tylko tekstowa lokalizacje.
    legacy_items = (
        db.query(models.Item)
        .filter(models.Item.location_id == None, models.Item.lokalizacja == location.name)
        .all()
    )
    for item in legacy_items:
        ensure_item_location(db, item)

    qr_codes: list[str] = []
    seen: set[str] = set()
    for raw_code in payload.qr_codes:
        code = extract_qr_code(raw_code)
        if code and code not in seen:
            qr_codes.append(code)
            seen.add(code)

    scanned_items = []
    if qr_codes:
        scanned_items = db.query(models.Item).filter(models.Item.qr_code.in_(qr_codes)).all()

    for item in scanned_items:
        ensure_item_location(db, item)

    expected_items = (
        db.query(models.Item)
        .filter(models.Item.location_id == location.id)
        .order_by(models.Item.nazwa, models.Item.id)
        .all()
    )

    found_codes = {item.qr_code for item in scanned_items}
    expected_codes = {item.qr_code for item in expected_items}
    unknown_codes = [code for code in qr_codes if code not in found_codes]

    present_items = [
        inventory_item_read(item, scanned=True)
        for item in expected_items
        if item.qr_code in seen
    ]
    missing_items = [
        inventory_item_read(item, scanned=False)
        for item in expected_items
        if item.qr_code not in seen
    ]

    wrong_location_items: list[WrongLocationItem] = []
    for item in scanned_items:
        if item.qr_code in expected_codes:
            continue

        expected_location = item_location_name(item)
        wrong_location_items.append(
            WrongLocationItem(
                **inventory_item_read(item, scanned=True).model_dump(),
                expected_location=expected_location,
                checked_location=location.name,
                message=(
                    f'Przedmiot "{item.nazwa}" powinien byc w lokalizacji '
                    f'"{expected_location}", a nie w "{location.name}".'
                ),
            )
        )

    db.commit()

    return LocationInventoryCheckRead(
        location=location_read(location),
        scanned_count=len(qr_codes),
        expected_count=len(expected_items),
        present_count=len(present_items),
        missing_count=len(missing_items),
        wrong_location_count=len(wrong_location_items),
        unknown_codes=unknown_codes,
        present_items=present_items,
        missing_items=missing_items,
        wrong_location_items=wrong_location_items,
    )
