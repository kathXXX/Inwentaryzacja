import os

import models
from database import SessionLocal
from models import UserRole
from security import hash_password


def seed_initial_admin():
    username = os.getenv("INITIAL_ADMIN_USERNAME")
    password = os.getenv("INITIAL_ADMIN_PASSWORD")

    if not username or not password:
        return

    db = SessionLocal()
    try:
        existing_user = db.query(models.User).filter(models.User.username == username).first()
        if existing_user:
            changed = False
            email = os.getenv("INITIAL_ADMIN_EMAIL")
            if email and not existing_user.email:
                existing_user.email = email
                changed = True
            if not existing_user.is_active:
                existing_user.is_active = True
                existing_user.activation_token = None
                existing_user.activation_token_expires_at = None
                changed = True
            if changed:
                db.commit()
            return

        admin = models.User(
            username=username,
            password=hash_password(password),
            is_active=True,
            activation_token=None,
            activation_token_expires_at=None,
            role=UserRole.administrator,
            first_name=os.getenv("INITIAL_ADMIN_FIRST_NAME", "Admin"),
            last_name=os.getenv("INITIAL_ADMIN_LAST_NAME", "Local"),
            email=os.getenv("INITIAL_ADMIN_EMAIL"),
            phone=os.getenv("INITIAL_ADMIN_PHONE"),
            field_of_study=None,
            student_index=None,
            department=os.getenv("INITIAL_ADMIN_DEPARTMENT"),
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()
