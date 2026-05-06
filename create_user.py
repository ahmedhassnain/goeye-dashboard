import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from passlib.context import CryptContext
from database import SessionLocal
from models.users import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user(username, email, full_name, password, role="analyst"):
    session = SessionLocal()
    try:
        existing = session.query(User).filter(User.username == username).first()
        if existing:
            print(f"User '{username}' already exists.")
            return

        user = User(
            username        = username,
            email           = email,
            full_name       = full_name,
            hashed_password = pwd_context.hash(password),
            role            = role,
        )
        session.add(user)
        session.commit()
        print(f"✓ User '{username}' created successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    # Usage: python create_user.py
    # Fill in the credentials below to create your initial user accounts.
    # Passwords are hashed with bcrypt before being stored - never commit real passwords here.
    create_user(
        username  = "admin_user",
        email     = "admin@example.com",
        full_name = "Admin User",
        password  = "change-me-before-use",
        role      = "Admin"
    )
    create_user(
        username  = "analyst_user",
        email     = "analyst@example.com",
        full_name = "Analyst User",
        password  = "change-me-before-use",
        role      = "Admin"
    )
    create_user(
        username  = "viewer_user",
        email     = "viewer@example.com",
        full_name = "Viewer User",
        password  = "change-me-before-use",
        role      = "Admin"
    )