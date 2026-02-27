from database_models import Base
from database import engine
from sqlalchemy import text

with engine.begin() as conn:
    for tbl in ['section1_sessions', 'section2_sessions', 'section3_sessions']:
        try:
            conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN face_violations INTEGER DEFAULT 0;"))
            print(f"Added face_violations to {tbl}")
        except Exception as e:
            print(e)
        try:
            conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN tab_violations INTEGER DEFAULT 0;"))
            print(f"Added tab_violations to {tbl}")
        except Exception as e:
            print(e)
