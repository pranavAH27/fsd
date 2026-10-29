"""Create the first platform administrator from an interactive prompt."""
import getpass
from sqlalchemy import func
from .database import Base, engine, SessionLocal
from .models import User
from .security import hash_password


def main():
    Base.metadata.create_all(bind=engine)
    name = input("Administrator name: ").strip()
    email = input("Administrator email: ").strip().lower()
    password = getpass.getpass("Password (8+ characters): ")
    if len(name) < 2 or len(password) < 8:
        raise SystemExit("Name must have at least 2 characters and password at least 8.")
    db = SessionLocal()
    try:
        if db.query(User).filter(func.lower(User.email) == email).first():
            raise SystemExit("That email already exists. Use an unused admin email.")
        user = User(name=name, email=email, password_hash=hash_password(password), role="admin", is_verified=True)
        db.add(user); db.commit()
        print(f"Administrator created: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
