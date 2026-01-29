"""
Test script that simulates 10 fake detections and verifies they are saved
to the database and image folder.

This script:
1. Creates 10 fake detection images with bounding boxes
2. Logs them using VisionLogger
3. Verifies they are saved to the database
4. Verifies images are saved to disk
5. Prints a comprehensive report

Usage:
    python tests/test_fake_detections.py
"""

import sys
import os
from pathlib import Path
import time
from datetime import datetime, timedelta
import random
import numpy as np
import cv2
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logging_service import VisionLogger, LoggingServiceConfig, DatabaseConfig, StorageConfig
from src.logging_service.database import SessionManager, PredictionLog


class FakeDetectionGenerator:
    """Generate fake detection images and metadata for testing."""

    def __init__(self, width: int = 640, height: int = 480):
        """
        Initialize fake detection generator.
        
        Args:
            width: Image width in pixels
            height: Image height in pixels
        """
        self.width = width
        self.height = height
        self.defect_types = [
            "scratch", "dent", "crack", "discoloration", 
            "missing_part", "misalignment", "corrosion", "burn_mark"
        ]
        self.colors = [
            (0, 0, 255),    # Red
            (0, 255, 0),    # Green
            (255, 0, 0),    # Blue
            (0, 255, 255),  # Yellow
            (255, 0, 255),  # Magenta
            (255, 255, 0),  # Cyan
        ]

    def generate_fake_image(
        self, 
        image_id: str, 
        has_defect: bool = True,
        num_boxes: int = None
    ) -> np.ndarray:
        """
        Generate a fake detection image with random shapes and bounding boxes.
        
        Args:
            image_id: Unique identifier for the image
            has_defect: Whether to draw defect indicators
            num_boxes: Number of bounding boxes to draw (random 1-5 if None)
            
        Returns:
            Generated image as numpy array (BGR format)
        """
        # Create blank image with random background
        bg_color = random.randint(50, 150)
        image = np.full((self.height, self.width, 3), bg_color, dtype=np.uint8)
        
        # Add some noise
        noise = np.random.randint(-30, 30, (self.height, self.width, 3), dtype=np.int16)
        image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        # Add grid pattern to make it look more industrial
        for i in range(0, self.width, 50):
            cv2.line(image, (i, 0), (i, self.height), (bg_color + 10, bg_color + 10, bg_color + 10), 1)
        for i in range(0, self.height, 50):
            cv2.line(image, (0, i), (self.width, i), (bg_color + 10, bg_color + 10, bg_color + 10), 1)
        
        # Add text label
        cv2.putText(
            image, 
            f"Test Image: {image_id}", 
            (10, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.7, 
            (255, 255, 255), 
            2
        )
        
        if has_defect:
            # Determine number of boxes
            if num_boxes is None:
                num_boxes = random.randint(1, 5)
            
            # Draw random "defect" regions
            for i in range(num_boxes):
                x = random.randint(50, self.width - 150)
                y = random.randint(50, self.height - 150)
                w = random.randint(50, 150)
                h = random.randint(50, 100)
                
                # Draw semi-transparent red rectangle for "defect"
                overlay = image.copy()
                cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 0, 200), -1)
                image = cv2.addWeighted(overlay, 0.3, image, 0.7, 0)
                
                # Draw bounding box
                color = self.colors[i % len(self.colors)]
                cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
                
                # Add label
                defect_label = random.choice(self.defect_types)
                cv2.putText(
                    image, 
                    defect_label, 
                    (x, y - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, 
                    color, 
                    2
                )
        else:
            # Draw "OK" indicator
            cv2.putText(
                image, 
                "OK - No Defects", 
                (self.width // 2 - 100, self.height // 2), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                1.0, 
                (0, 255, 0), 
                3
            )
        
        return image

    def generate_fake_bounding_boxes(
        self, 
        has_defect: bool = True, 
        num_boxes: int = None
    ) -> List[Dict[str, Any]]:
        """
        Generate fake bounding box data.
        
        Args:
            has_defect: Whether defects are present
            num_boxes: Number of boxes to generate (random 1-5 if None)
            
        Returns:
            List of bounding box dictionaries
        """
        if not has_defect:
            return []
        
        if num_boxes is None:
            num_boxes = random.randint(1, 5)
        
        boxes = []
        for _ in range(num_boxes):
            x = random.randint(50, self.width - 150)
            y = random.randint(50, self.height - 150)
            w = random.randint(50, 150)
            h = random.randint(50, 100)
            
            boxes.append({
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "confidence": round(random.uniform(0.6, 0.99), 3),
                "class": random.choice(self.defect_types),
            })
        
        return boxes


class DetectionTestSuite:
    """Test suite for verifying detection logging."""

    def __init__(self, test_dir: str = "./test_outputs"):
        """
        Initialize test suite.
        
        Args:
            test_dir: Directory for test outputs
        """
        self.test_dir = Path(test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging service for testing
        self.config = LoggingServiceConfig(
            database=DatabaseConfig(
                url=f"sqlite:///{self.test_dir}/test_vision_logs.db",
                echo=False,
                auto_migrate=True,
            ),
            storage=StorageConfig(
                base_path=str(self.test_dir / "test_prediction_images"),
                organize_by_date=True,
                organize_by_result=True,
                image_quality=90,
            ),
            model_version="test-v1.0",
            model_name="test-yolov8n",
        )
        
        self.logger = VisionLogger(config=self.config)
        self.generator = FakeDetectionGenerator()
        self.logged_ids = []
        self.results = {
            "total": 0,
            "defects": 0,
            "no_defects": 0,
            "db_verified": 0,
            "image_verified": 0,
            "errors": [],
        }

    def generate_and_log_detection(
        self, 
        detection_num: int, 
        has_defect: bool = None
    ) -> Dict[str, Any]:
        """
        Generate and log a single fake detection.
        
        Args:
            detection_num: Detection number (for naming)
            has_defect: Whether to include defects (random if None)
            
        Returns:
            Dictionary with detection details
        """
        if has_defect is None:
            has_defect = random.choice([True, True, True, False])  # 75% defects
        
        # Generate unique image ID
        timestamp = datetime.utcnow() - timedelta(seconds=detection_num)
        image_id = f"test_detection_{detection_num:03d}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        # Generate fake image
        num_boxes = random.randint(1, 5) if has_defect else 0
        image = self.generator.generate_fake_image(image_id, has_defect, num_boxes)
        
        # Generate fake bounding boxes
        bounding_boxes = self.generator.generate_fake_bounding_boxes(has_defect, num_boxes)
        
        # Generate fake metadata
        confidence = round(random.uniform(0.7, 0.99), 3) if has_defect else round(random.uniform(0.1, 0.3), 3)
        defect_type = random.choice(self.generator.defect_types) if has_defect else None
        inference_time_ms = round(random.uniform(20.0, 80.0), 2)
        
        # Log the detection
        try:
            log_id = self.logger.log_prediction(
                image=image,
                image_id=image_id,
                confidence=confidence,
                defect_detected=has_defect,
                timestamp=timestamp,
                defect_type=defect_type,
                bounding_boxes=bounding_boxes,
                inference_time_ms=inference_time_ms,
                processing_notes=f"Test detection #{detection_num}",
            )
            
            detection_info = {
                "log_id": log_id,
                "image_id": image_id,
                "has_defect": has_defect,
                "confidence": confidence,
                "num_boxes": len(bounding_boxes),
                "defect_type": defect_type,
                "inference_time_ms": inference_time_ms,
                "timestamp": timestamp,
            }
            
            self.logged_ids.append(log_id)
            self.results["total"] += 1
            if has_defect:
                self.results["defects"] += 1
            else:
                self.results["no_defects"] += 1
            
            print(f"✓ Logged detection #{detection_num}: id={log_id}, defect={has_defect}, boxes={len(bounding_boxes)}")
            
            return detection_info
            
        except Exception as e:
            error_msg = f"Failed to log detection #{detection_num}: {e}"
            print(f"✗ {error_msg}")
            self.results["errors"].append(error_msg)
            raise

    def verify_database_entries(self) -> bool:
        """
        Verify all detections are in the database.
        
        Returns:
            True if all entries verified, False otherwise
        """
        print("\n" + "=" * 70)
        print("VERIFYING DATABASE ENTRIES")
        print("=" * 70)
        
        all_verified = True
        
        with SessionManager(self.logger.db_connection) as session:
            for log_id in self.logged_ids:
                entry = session.query(PredictionLog).filter(
                    PredictionLog.id == log_id
                ).first()
                
                if entry:
                    print(f"✓ Found in DB: id={entry.id}, image_id={entry.image_id}, defect={entry.defect_detected}")
                    self.results["db_verified"] += 1
                else:
                    print(f"✗ NOT FOUND in DB: id={log_id}")
                    all_verified = False
                    self.results["errors"].append(f"Database entry {log_id} not found")
        
        # Query summary statistics
        with SessionManager(self.logger.db_connection) as session:
            total_count = session.query(PredictionLog).count()
            defect_count = session.query(PredictionLog).filter(
                PredictionLog.defect_detected == True
            ).count()
            no_defect_count = total_count - defect_count
            
            print(f"\nDatabase Summary:")
            print(f"  Total entries: {total_count}")
            print(f"  Defects: {defect_count}")
            print(f"  No defects: {no_defect_count}")
        
        return all_verified

    def verify_image_files(self) -> bool:
        """
        Verify all images are saved to disk.
        
        Returns:
            True if all images verified, False otherwise
        """
        print("\n" + "=" * 70)
        print("VERIFYING IMAGE FILES")
        print("=" * 70)
        
        all_verified = True
        
        with SessionManager(self.logger.db_connection) as session:
            for log_id in self.logged_ids:
                entry = session.query(PredictionLog).filter(
                    PredictionLog.id == log_id
                ).first()
                
                if entry:
                    image_path = Path(entry.image_path)
                    if image_path.exists():
                        # Verify it's a valid image
                        try:
                            img = cv2.imread(str(image_path))
                            if img is not None:
                                print(f"✓ Image exists: {image_path.name} (shape: {img.shape})")
                                self.results["image_verified"] += 1
                            else:
                                print(f"✗ Image corrupted: {image_path}")
                                all_verified = False
                                self.results["errors"].append(f"Image corrupted: {image_path}")
                        except Exception as e:
                            print(f"✗ Error reading image {image_path}: {e}")
                            all_verified = False
                            self.results["errors"].append(f"Error reading {image_path}: {e}")
                    else:
                        print(f"✗ Image NOT FOUND: {image_path}")
                        all_verified = False
                        self.results["errors"].append(f"Image file not found: {image_path}")
        
        # Count actual files on disk
        image_dir = Path(self.config.storage.base_path)
        if image_dir.exists():
            image_files = list(image_dir.rglob("*.jpg")) + list(image_dir.rglob("*.png"))
            print(f"\nImage Directory Summary:")
            print(f"  Base path: {image_dir}")
            print(f"  Total image files: {len(image_files)}")
        
        return all_verified

    def print_final_report(self):
        """Print comprehensive test report."""
        print("\n" + "=" * 70)
        print("FINAL TEST REPORT")
        print("=" * 70)
        
        print(f"\nGeneration & Logging:")
        print(f"  Total detections logged: {self.results['total']}")
        print(f"  With defects: {self.results['defects']}")
        print(f"  Without defects: {self.results['no_defects']}")
        
        print(f"\nVerification:")
        print(f"  Database entries verified: {self.results['db_verified']}/{self.results['total']}")
        print(f"  Image files verified: {self.results['image_verified']}/{self.results['total']}")
        
        if self.results["errors"]:
            print(f"\nErrors ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                print(f"  - {error}")
        
        # Overall status
        print("\n" + "=" * 70)
        if (
            self.results["db_verified"] == self.results["total"] and 
            self.results["image_verified"] == self.results["total"] and 
            len(self.results["errors"]) == 0
        ):
            print("✓ ALL TESTS PASSED")
            print("=" * 70)
            return True
        else:
            print("✗ SOME TESTS FAILED")
            print("=" * 70)
            return False

    def run_full_test(self, num_detections: int = 10):
        """
        Run complete test suite.
        
        Args:
            num_detections: Number of fake detections to generate
        """
        print("=" * 70)
        print(f"FAKE DETECTION TEST SUITE - {num_detections} DETECTIONS")
        print("=" * 70)
        print(f"\nTest Configuration:")
        print(f"  Database: {self.config.database.url}")
        print(f"  Images: {self.config.storage.base_path}")
        print(f"  Model: {self.config.model_name} v{self.config.model_version}")
        print("")
        
        # Step 1: Generate and log detections
        print("\n" + "=" * 70)
        print("STEP 1: GENERATING AND LOGGING DETECTIONS")
        print("=" * 70)
        
        detection_infos = []
        for i in range(1, num_detections + 1):
            try:
                info = self.generate_and_log_detection(i)
                detection_infos.append(info)
                time.sleep(0.1)  # Small delay for realistic timestamps
            except Exception as e:
                print(f"Failed to create detection #{i}: {e}")
        
        # Step 2: Verify database entries
        db_ok = self.verify_database_entries()
        
        # Step 3: Verify image files
        images_ok = self.verify_image_files()
        
        # Step 4: Print final report
        all_passed = self.print_final_report()
        
        return all_passed


def main():
    """Main entry point."""
    print("\n" + "=" * 70)
    print("FAKE DETECTION LOGGING TEST SCRIPT")
    print("=" * 70)
    print("This script generates 10 fake detections and verifies they are")
    print("properly saved to the database and image folder.")
    print("")
    
    # Create test suite
    test_suite = DetectionTestSuite(test_dir="./test_outputs")
    
    # Run test
    success = test_suite.run_full_test(num_detections=10)
    
    # Exit with appropriate code
    if success:
        print("\n✓ Test completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Test completed with failures!")
        sys.exit(1)


if __name__ == "__main__":
    main()
