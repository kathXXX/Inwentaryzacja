from sqlalchemy.orm import Session

import models


def normalize_location_name(name: str) -> str:
    return " ".join((name or "").strip().split())


def get_or_create_location(db: Session, name: str) -> models.Location:
    normalized = normalize_location_name(name)
    if not normalized:
        raise ValueError("Lokalizacja jest wymagana")

    location = db.query(models.Location).filter(models.Location.name == normalized).first()
    if location:
        return location

    location = models.Location(name=normalized)
    db.add(location)
    db.flush()
    return location


def ensure_item_location(db: Session, item: models.Item) -> models.Location:
    if item.location:
        return item.location

    location = get_or_create_location(db, item.lokalizacja)
    item.location_id = location.id
    item.lokalizacja = location.name
    return location


def item_location_name(item: models.Item) -> str:
    return item.location.name if item.location else item.lokalizacja
