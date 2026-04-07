import os
import sys

# Ensure backend directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
import models
import auth

from sqlalchemy import text

def create_god_user():
    db = SessionLocal()
    try:
        # PostgreSQL SQLAlchemy Enum defaults to using names instead of values in schema
        db.execute(text("ALTER TYPE roleenum ADD VALUE 'GENERAL_COORDINATOR';"))
        db.commit()
    except Exception as e:
        db.rollback()
        print("Enum perhaps already fixed")
        
    try:
        email = "coord.general@espora.unam.mx"
        password = "admin123"
        
        # Check if exists
        user = db.query(models.User).filter(models.User.email == email).first()
        if user:
            print(f"User {email} already exists!")
            return
            
        hashed_password = auth.get_password_hash(password)
        
        # Create general coordinator
        new_user = models.User(
            email=email,
            hashed_password=hashed_password,
            role=models.RoleEnum.GENERAL_COORDINATOR,
            is_active=True,
            full_name="Coordinación General ESPORA",
            site_id=None # Super user has no specific site bind
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"✅ Successfully created General Coordinator!")
        print(f"📧 Email: {email}")
        print(f"🔑 Password: {password}")
        
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_god_user()
