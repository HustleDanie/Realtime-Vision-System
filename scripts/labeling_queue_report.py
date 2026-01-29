#!/usr/bin/env python3
"""
Labeling Queue Verification Report

Generates a comprehensive report showing:
1. Queue statistics
2. Confidence distribution
3. Defect breakdown
4. Pending items sample
5. Database integrity check
"""

import sqlite3
import json
from datetime import datetime
from collections import defaultdict

def generate_report():
    """Generate comprehensive labeling queue report."""
    conn = sqlite3.connect('vision_logs.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n" + "=" * 100)
    print("LABELING QUEUE - COMPREHENSIVE VERIFICATION REPORT")
    print("=" * 100)
    print(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Queue Statistics
    print("1. QUEUE STATISTICS")
    print("-" * 100)
    
    cursor.execute("SELECT COUNT(*) FROM labeling_queue")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM labeling_queue WHERE status = 'pending'")
    pending = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM labeling_queue WHERE status = 'completed'")
    completed = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM labeling_queue WHERE status = 'rejected'")
    rejected = cursor.fetchone()[0]
    
    print(f"Total Items: {total}")
    print(f"  • Pending:   {pending} ({pending/total*100:.1f}%)")
    print(f"  • Completed: {completed} ({completed/total*100 if total > 0 else 0:.1f}%)")
    print(f"  • Rejected:  {rejected} ({rejected/total*100 if total > 0 else 0:.1f}%)")
    print()
    
    # 2. Confidence Distribution
    print("2. CONFIDENCE DISTRIBUTION")
    print("-" * 100)
    
    cursor.execute("""
        SELECT 
            CASE 
                WHEN confidence_score < 0.2 THEN 'Very Low (0.0-0.2)'
                WHEN confidence_score < 0.3 THEN 'Low (0.2-0.3)'
                WHEN confidence_score < 0.4 THEN 'Medium (0.3-0.4)'
                WHEN confidence_score < 0.5 THEN 'High (0.4-0.5)'
                ELSE 'Very High (>0.5)'
            END as range,
            COUNT(*) as count
        FROM labeling_queue
        WHERE status = 'pending'
        GROUP BY range
        ORDER BY count DESC
    """)
    
    for row in cursor.fetchall():
        count = row['count']
        pct = count / pending * 100 if pending > 0 else 0
        print(f"  {row['range']:<20}: {count:>3} items ({pct:>5.1f}%) {'█' * int(pct/5)}")
    print()
    
    # 3. Defect Analysis
    print("3. DEFECT BREAKDOWN")
    print("-" * 100)
    
    cursor.execute("""
        SELECT 
            defect_detected,
            COUNT(*) as count
        FROM labeling_queue
        WHERE status = 'pending'
        GROUP BY defect_detected
    """)
    
    for row in cursor.fetchall():
        defect_label = "Defect Detected" if row['defect_detected'] else "No Defect"
        count = row['count']
        pct = count / pending * 100 if pending > 0 else 0
        print(f"  {defect_label:<25}: {count:>3} items ({pct:>5.1f}%)")
    print()
    
    # 4. Confidence Statistics
    print("4. CONFIDENCE STATISTICS (Pending Items)")
    print("-" * 100)
    
    cursor.execute("""
        SELECT 
            MIN(confidence_score) as min_conf,
            MAX(confidence_score) as max_conf,
            AVG(confidence_score) as avg_conf,
            COUNT(*) as count
        FROM labeling_queue
        WHERE status = 'pending'
    """)
    
    row = cursor.fetchone()
    if row and row['count'] > 0:
        print(f"  Minimum:  {row['min_conf']:.4f}")
        print(f"  Maximum:  {row['max_conf']:.4f}")
        print(f"  Average:  {row['avg_conf']:.4f}")
        print(f"  Count:    {row['count']}")
    print()
    
    # 5. Model Statistics
    print("5. MODEL INFORMATION")
    print("-" * 100)
    
    cursor.execute("""
        SELECT 
            model_name,
            model_version,
            COUNT(*) as count,
            AVG(confidence_score) as avg_conf
        FROM labeling_queue
        WHERE status = 'pending'
        GROUP BY model_name, model_version
    """)
    
    for row in cursor.fetchall():
        print(f"  {row['model_name']} ({row['model_version']})")
        print(f"    Items: {row['count']} | Avg Confidence: {row['avg_conf']:.4f}")
    print()
    
    # 6. Sample Pending Items
    print("6. SAMPLE PENDING ITEMS (First 10)")
    print("-" * 100)
    
    cursor.execute("""
        SELECT 
            id,
            image_id,
            confidence_score,
            defect_detected,
            model_name,
            timestamp
        FROM labeling_queue
        WHERE status = 'pending'
        ORDER BY timestamp ASC
        LIMIT 10
    """)
    
    for i, row in enumerate(cursor.fetchall(), 1):
        defect = "YES" if row['defect_detected'] else "NO"
        print(f"  {i:2d}. ID: {row['id']:3d} | Confidence: {row['confidence_score']:.3f} | Defect: {defect} | {row['image_id']}")
    print()
    
    # 7. Database Integrity
    print("7. DATABASE INTEGRITY CHECK")
    print("-" * 100)
    
    # Check for duplicate image_ids
    cursor.execute("""
        SELECT image_id, COUNT(*) as count
        FROM labeling_queue
        GROUP BY image_id
        HAVING count > 1
    """)
    
    duplicates = cursor.fetchall()
    if duplicates:
        print(f"  ✗ WARNING: Found {len(duplicates)} duplicate image_ids")
        for row in duplicates:
            print(f"    • {row['image_id']}: {row['count']} entries")
    else:
        print("  ✓ No duplicate image_ids found")
    
    # Check for NULL values
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN confidence_score IS NULL THEN 1 END) as null_conf,
            COUNT(CASE WHEN model_name IS NULL THEN 1 END) as null_model,
            COUNT(CASE WHEN timestamp IS NULL THEN 1 END) as null_ts
        FROM labeling_queue
    """)
    
    row = cursor.fetchone()
    null_issues = row['null_conf'] + row['null_model'] + row['null_ts']
    
    if null_issues > 0:
        print(f"  ✗ WARNING: Found {null_issues} NULL values in important fields")
    else:
        print("  ✓ No NULL values in important fields")
    
    # Check for status values
    cursor.execute("""
        SELECT DISTINCT status FROM labeling_queue
    """)
    
    valid_statuses = {'pending', 'completed', 'rejected'}
    found_statuses = {row['status'] for row in cursor.fetchall()}
    invalid = found_statuses - valid_statuses
    
    if invalid:
        print(f"  ✗ WARNING: Found invalid status values: {invalid}")
    else:
        print("  ✓ All status values are valid")
    
    print()
    
    # 8. Summary
    print("8. SUMMARY")
    print("-" * 100)
    print(f"✓ Labeling queue is operational")
    print(f"✓ {total} predictions in queue")
    print(f"✓ {pending} pending items awaiting human review")
    if completed > 0:
        print(f"✓ {completed} items completed")
    print(f"✓ Average confidence of pending: {cursor.execute('SELECT AVG(confidence_score) FROM labeling_queue WHERE status = \"pending\"').fetchone()[0]:.3f}")
    print()
    
    print("=" * 100)
    print("Report Complete")
    print("=" * 100 + "\n")
    
    conn.close()

if __name__ == "__main__":
    generate_report()
