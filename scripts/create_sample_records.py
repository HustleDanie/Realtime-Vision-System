"""
Create sample database records without image generation (no CV2 dependency).
Quick way to populate the database for testing queries.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
import sqlite3

# Sample data
DEFECT_TYPES = ["scratch", "dent", "crack", "discoloration", "burn_mark"]
MODEL_NAMES = ["yolov8n", "yolov8s", "yolov8m"]

def create_sample_records(db_path="./vision_logs.db", count=10):
    """Create sample prediction records."""
    
    print(f"Creating {count} sample records in {db_path}...")
    
    # Connect and create table if needed
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id VARCHAR(255) NOT NULL UNIQUE,
            image_path VARCHAR(512) NOT NULL,
            timestamp DATETIME NOT NULL,
            model_version VARCHAR(50) NOT NULL,
            model_name VARCHAR(100) NOT NULL,
            confidence_score FLOAT NOT NULL,
            defect_detected BOOLEAN NOT NULL,
            defect_type VARCHAR(100),
            bounding_boxes TEXT,
            inference_time_ms FLOAT,
            processing_notes TEXT
        )
    """)
    
    # Insert records
    for i in range(1, count + 1):
        has_defect = random.choice([True, True, True, False])  # 75% defects
        timestamp = datetime.utcnow() - timedelta(minutes=count - i)
        image_id = f"sample_{i:04d}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        cursor.execute("""
            INSERT INTO prediction_logs 
            (image_id, image_path, timestamp, model_version, model_name,
             confidence_score, defect_detected, defect_type, bounding_boxes,
             inference_time_ms, processing_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            image_id,
            f"./prediction_images/{timestamp.strftime('%Y/%m/%d')}/{'defects' if has_defect else 'no_defects'}/{image_id}.jpg",
            timestamp.isoformat(),
            "v1.0",
            random.choice(MODEL_NAMES),
            round(random.uniform(0.7, 0.99) if has_defect else random.uniform(0.1, 0.3), 3),
            has_defect,
            random.choice(DEFECT_TYPES) if has_defect else None,
            None,  # No bounding boxes for simplicity
            round(random.uniform(20.0, 80.0), 2),
            f"Sample record #{i}"
        ))
        
        print(f"✓ Created record #{i}: {image_id} (defect={has_defect})")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Successfully created {count} sample records!")
    print(f"📁 Database: {db_path}")
    print(f"\nNow you can query them with:")
    print(f"    python scripts/query_last_records.py --db {db_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create sample database records")
    parser.add_argument("--db", default="./vision_logs.db", help="Database path")
    parser.add_argument("--count", type=int, default=10, help="Number of records")
    args = parser.parse_args()
    
    create_sample_records(args.db, args.count)
