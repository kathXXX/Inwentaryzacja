import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from urllib.parse import quote_plus

password = quote_plus("MaKaLuKl1")  # safely encodes @, Ł, etc.

URL_DATABASE = os.getenv("DATABASE_URL")

if not URL_DATABASE:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(URL_DATABASE, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()