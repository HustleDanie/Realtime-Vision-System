"""
Query and display the last 5 inspection records from the database.

Usage:
    python scripts/query_last_records.py
    python scripts/query_last_records.py --count 10
    python scripts/query_last_records.py --db ./vision_logs.db
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import json
import sqlite3


def format_timestamp(dt_str):
    """Format datetime string for display."""
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str


def format_bounding_boxes(bbox_json):
    """Format bounding boxes for display."""
    if not bbox_json:
        return "None"
    
    try:
        boxes = json.loads(bbox_json)
        if not boxes:
            return "None"
        return f"{len(boxes)} box(es)"
    except:
        return "Invalid"


def print_record(record, index=None):
    """Print a single record in a formatted way."""
    prefix = f"[{index}] " if index is not None else ""
    
    id_val, image_id, image_path, timestamp, model_version, model_name, \
    confidence, defect_detected, defect_type, bboxes, inference_time, notes = record
    
    print(f"\n{prefix}{'=' * 70}")
    print(f"ID: {id_val}")
    print(f"Image ID: {image_id}")
    print(f"Timestamp: {format_timestamp(timestamp)}")
    print(f"Model: {model_name} (v{model_version})")
    print(f"Defect Detected: {'YES' if defect_detected else 'NO'}")
    print(f"Confidence: {confidence:.3f}")
    
    if defect_type:
        print(f"Defect Type: {defect_type}")
    
    print(f"Bounding Boxes: {format_bounding_boxes(bboxes)}")
    
    if inference_time:
        print(f"Inference Time: {inference_time:.2f} ms")
    
    print(f"Image Path: {image_path}")
    
    if notes:
        print(f"Notes: {notes}")
    
    print("=" * 70)


def query_last_records(db_path, count=5, defect_only=False):
    """
    Query and display the last N records from the database.
    
    Args:
        db_path: Database file path
        count: Number of records to retrieve
        defect_only: If True, only show records with defects
    """
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"\n{'=' * 70}")
        print(f"QUERYING DATABASE: {db_path}")
        print(f"{'=' * 70}")
        
        # Build query
        query = """
            SELECT id, image_id, image_path, timestamp, model_version, model_name,
                   confidence_score, defect_detected, defect_type, bounding_boxes,
                   inference_time_ms, processing_notes
            FROM prediction_logs
        """
        
        if defect_only:
            query += " WHERE defect_detected = 1"
        
        query += " ORDER BY id DESC LIMIT ?"
        
        # Execute query
        cursor.execute(query, (count,))
        records = cursor.fetchall()
        
        if not records:
            print("\n⚠️  No records found in database")
            conn.close()
            return
        
        # Print summary
        print(f"\nFound {len(records)} record(s)")
        filter_text = " (defects only)" if defect_only else ""
        print(f"Showing last {len(records)} inspection(s){filter_text}:\n")
        
        # Print each record
        for i, record in enumerate(records, 1):
            print_record(record, index=i)
        
        # Print statistics
        print(f"\n{'=' * 70}")
        print("DATABASE STATISTICS")
        print(f"{'=' * 70}")
        
        cursor.execute("SELECT COUNT(*) FROM prediction_logs")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM prediction_logs WHERE defect_detected = 1")
        defect_count = cursor.fetchone()[0]
        no_defect_count = total_count - defect_count
        
        print(f"Total Records: {total_count}")
        if total_count > 0:
            print(f"With Defects: {defect_count} ({defect_count/total_count*100:.1f}%)")
            print(f"Without Defects: {no_defect_count} ({no_defect_count/total_count*100:.1f}%)")
        else:
            print(f"With Defects: 0")
            print(f"Without Defects: 0")
        print("=" * 70)
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error querying database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Query and display the last N inspection records from the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/query_last_records.py
  python scripts/query_last_records.py --count 10
  python scripts/query_last_records.py --defects-only
  python scripts/query_last_records.py --db ./custom_logs.db --count 20
        """
    )
    
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of records to retrieve (default: 5)"
    )
    
    parser.add_argument(
        "--db",
        type=str,
        default="./vision_logs.db",
        help="Database file path (default: ./vision_logs.db)"
    )
    
    parser.add_argument(
        "--defects-only",
        action="store_true",
        help="Only show records with defects detected"
    )
    
    args = parser.parse_args()
    
    # Validate count
    if args.count < 1 or args.count > 1000:
        print("❌ Error: Count must be between 1 and 1000")
        sys.exit(1)
    
    # Check if database exists
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"❌ Error: Database file not found: {args.db}")
        print(f"\nTip: Run the detection pipeline first or create test data:")
        print(f"     python run_realtime_detection.py --enable-logging")
        print(f"     python tests/test_fake_detections.py")
        sys.exit(1)
    
    # Query and display records
    query_last_records(str(db_path), count=args.count, defect_only=args.defects_only)


if __name__ == "__main__":
    main()
