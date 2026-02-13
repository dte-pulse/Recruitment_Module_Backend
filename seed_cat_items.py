"""
Seed CAT Items from item_bank.json
Populates the cat_items table if it's empty
"""

import json
from sqlalchemy.orm import Session
from database import SessionLocal
import database_models

def seed_cat_items():
    """Load CAT items from item_bank.json into the database if table is empty"""
    
    db: Session = SessionLocal()
    
    try:
        # Check if table already has data
        existing_count = db.query(database_models.CATItem).count()
        
        if existing_count > 0:
            print(f"✓ CAT items table already has {existing_count} items. Skipping seed.")
            return
        
        # Load JSON file
        print("📂 Loading item_bank.json...")
        with open('item_bank.json', 'r', encoding='utf-8') as f:
            items_data = json.load(f)
        
        print(f"📊 Found {len(items_data)} items in JSON file")
        
        # Convert correct index to letter (0->A, 1->B, 2->C, 3->D)
        index_to_letter = {0: 'A', 1: 'B', 2: 'C', 3: 'D'}
        
        # Insert items
        inserted_count = 0
        for item_data in items_data:
            # Map options array to individual columns
            options = item_data.get('options', [])
            
            # Ensure we have 4 options
            while len(options) < 4:
                options.append("")
            
            # Convert correct index to letter
            correct_index = item_data.get('correct', 0)
            correct_letter = index_to_letter.get(correct_index, 'A')
            
            # Create CAT item
            cat_item = database_models.CATItem(
                question=item_data.get('question', ''),
                option_a=options[0] if len(options) > 0 else '',
                option_b=options[1] if len(options) > 1 else '',
                option_c=options[2] if len(options) > 2 else '',
                option_d=options[3] if len(options) > 3 else '',
                correct=correct_letter,
                a=item_data.get('a', 1.0),
                b=item_data.get('b', 0.0),
                c=item_data.get('c', 0.25),
                used_count=0,
                correct_count=0
            )
            
            db.add(cat_item)
            inserted_count += 1
        
        # Commit all items
        db.commit()
        print(f"✓ Successfully inserted {inserted_count} CAT items into database")
        
    except FileNotFoundError:
        print("✗ Error: item_bank.json not found")
    except json.JSONDecodeError as e:
        print(f"✗ Error parsing JSON: {e}")
    except Exception as e:
        print(f"✗ Error seeding CAT items: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🌱 Starting CAT Items Seeder...")
    seed_cat_items()
    print("✅ Seeding complete!")
