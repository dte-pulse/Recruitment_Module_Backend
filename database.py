# from sqlalchemy.orm import sessionmaker
# from sqlalchemy import create_engine

# # Update your database URL
# db_url = "postgresql://postgres:Stardust2%402020@localhost:5432/hrmodule"

# engine = create_engine(db_url, echo=False)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL from environment
db_url = os.getenv("DATABASE_URL")

if not db_url:
    raise ValueError("DATABASE_URL not found in environment variables")

engine = create_engine(db_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
