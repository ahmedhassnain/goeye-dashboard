import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Cloud deployments (Neon, Render) provide a single DATABASE_URL.
# Local development can use individual DB_* vars instead.
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Neon's pooled endpoints (host contains "-pooler") reject startup options, and
# public is already the default schema there, so only pin it on direct connections.
connect_args = {} if "-pooler." in DATABASE_URL else {"options": "-csearch_path=public"}

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine)
