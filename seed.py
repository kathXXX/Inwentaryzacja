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
            return

        admin = models.User(
            username=username,
            password=hash_password(password),
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
