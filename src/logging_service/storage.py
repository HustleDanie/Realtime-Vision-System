"""
Image storage management for ML vision logging system.
Handles organizing, saving, and retrieving prediction images on disk.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
import logging
import cv2
import hashlib

logger = logging.getLogger(__name__)


class ImageStorage:
    """
    Manages storage and organization of prediction images on disk.
    
    Storage structure:
    ```
    base_path/
    ├── YYYY/
    │   ├── MM/
    │   │   ├── DD/
    │   │   │   ├── defects/
    │   │   │   │   └── image_20240101_120000_uuid.jpg
    │   │   │   └── no_defects/
    │   │   │       └── image_20240101_120001_uuid.jpg
    ```
    """

    def __init__(
        self,
        base_path: str = "./prediction_images",
        organize_by_date: bool = True,
        organize_by_result: bool = True,
    ):
        """
        Initialize image storage manager.

        Args:
            base_path: Root directory for image storage
            organize_by_date: Whether to organize by YYYY/MM/DD
            organize_by_result: Whether to organize by defects/no_defects
        """
        self.base_path = Path(base_path)
        self.organize_by_date = organize_by_date
        self.organize_by_result = organize_by_result

        # Create base directory
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Image storage initialized at: {self.base_path}")

    def _get_storage_path(
        self,
        timestamp: datetime,
        defect_detected: bool,
    ) -> Path:
        """
        Determine storage path based on configuration.

        Args:
            timestamp: Timestamp of the prediction
            defect_detected: Whether a defect was detected

        Returns:
            Path where image should be stored
        """
        path = self.base_path

        if self.organize_by_date:
            year = timestamp.strftime("%Y")
            month = timestamp.strftime("%m")
            day = timestamp.strftime("%d")
            path = path / year / month / day

        if self.organize_by_result:
            result_dir = "defects" if defect_detected else "no_defects"
            path = path / result_dir

        path.mkdir(parents=True, exist_ok=True)
        return path

    def _generate_filename(
        self,
        image_id: str,
        timestamp: datetime,
    ) -> str:
        """
        Generate standardized filename for saved image.

        Args:
            image_id: Original image identifier
            timestamp: Timestamp of prediction

        Returns:
            Filename with timestamp and hash
        """
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        # Create short hash from image_id
        id_hash = hashlib.md5(image_id.encode()).hexdigest()[:8]
        filename = f"pred_{timestamp_str}_{id_hash}.jpg"
        return filename

    def save_labeling_image(
        self,
        image: 'cv2.Mat',
        image_id: str,
        timestamp: Optional[datetime] = None,
        quality: int = 95,
    ) -> str:
        """Save image to labeling queue folder."""
        if image is None or image.size == 0:
            raise ValueError("Invalid image provided")

        if timestamp is None:
            timestamp = datetime.utcnow()

        labeling_root = self.base_path / "labeling_queue"
        labeling_root.mkdir(parents=True, exist_ok=True)

        filename = self._generate_filename(image_id, timestamp)
        full_path = labeling_root / filename

        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        success = cv2.imwrite(str(full_path), image, encode_params)
        if not success:
            raise IOError(f"Failed to write labeling image to {full_path}")

        return str(full_path.relative_to(self.base_path))

    def save_image(
        self,
        image: 'cv2.Mat',
        image_id: str,
        timestamp: Optional[datetime] = None,
        defect_detected: bool = False,
        quality: int = 95,
    ) -> str:
        """
        Save prediction image to disk.

        Args:
            image: OpenCV image (numpy array)
            image_id: Unique identifier for the image
            timestamp: When prediction was made (defaults to now)
            defect_detected: Whether a defect was detected
            quality: JPEG quality (0-100)

        Returns:
            Relative path to saved image

        Raises:
            ValueError: If image is invalid
            IOError: If save operation fails
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid image provided")

        if timestamp is None:
            timestamp = datetime.utcnow()

        try:
            # Get storage path
            storage_path = self._get_storage_path(timestamp, defect_detected)

            # Generate filename
            filename = self._generate_filename(image_id, timestamp)

            # Full file path
            full_path = storage_path / filename

            # Save image
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            success = cv2.imwrite(str(full_path), image, encode_params)

            if not success:
                raise IOError(f"Failed to write image to {full_path}")

            # Return relative path
            relative_path = str(full_path.relative_to(self.base_path))
            logger.info(
                f"Image saved: {image_id} -> {relative_path} "
                f"(defect={defect_detected})"
            )
            return relative_path

        except Exception as e:
            logger.error(f"Error saving image {image_id}: {e}")
            raise

    def get_image_path(self, relative_path: str) -> Path:
        """
        Get full path to a stored image.

        Args:
            relative_path: Relative path returned from save_image

        Returns:
            Full path to image file
        """
        return self.base_path / relative_path

    def image_exists(self, relative_path: str) -> bool:
        """
        Check if image file exists.

        Args:
            relative_path: Relative path returned from save_image

        Returns:
            True if image exists, False otherwise
        """
        return self.get_image_path(relative_path).exists()

    def load_image(self, relative_path: str) -> 'cv2.Mat':
        """
        Load image from disk.

        Args:
            relative_path: Relative path returned from save_image

        Returns:
            OpenCV image (numpy array)

        Raises:
            FileNotFoundError: If image doesn't exist
        """
        full_path = self.get_image_path(relative_path)

        if not full_path.exists():
            raise FileNotFoundError(f"Image not found: {relative_path}")

        image = cv2.imread(str(full_path))
        if image is None:
            raise IOError(f"Failed to load image: {relative_path}")

        logger.debug(f"Image loaded: {relative_path}")
        return image

    def delete_image(self, relative_path: str) -> bool:
        """
        Delete image from disk.

        Args:
            relative_path: Relative path returned from save_image

        Returns:
            True if successful, False otherwise
        """
        try:
            full_path = self.get_image_path(relative_path)
            if full_path.exists():
                full_path.unlink()
                logger.info(f"Image deleted: {relative_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting image {relative_path}: {e}")
            return False

    def get_storage_stats(self) -> dict:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage information
        """
        stats = {
            "base_path": str(self.base_path),
            "total_images": 0,
            "defect_images": 0,
            "no_defect_images": 0,
            "total_size_mb": 0.0,
        }

        try:
            for img_file in self.base_path.rglob("*.jpg"):
                stats["total_images"] += 1
                stats["total_size_mb"] += img_file.stat().st_size / (1024 * 1024)

                if "defects" in str(img_file):
                    stats["defect_images"] += 1
                else:
                    stats["no_defect_images"] += 1

            logger.debug(f"Storage stats: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error calculating storage stats: {e}")
            return stats

    def cleanup_old_images(self, days_old: int = 30) -> int:
        """
        Delete images older than specified days.

        Args:
            days_old: Delete images older than this many days

        Returns:
            Number of images deleted
        """
        import time

        current_time = time.time()
        cutoff_time = current_time - (days_old * 86400)
        deleted_count = 0

        try:
            for img_file in self.base_path.rglob("*.jpg"):
                if img_file.stat().st_mtime < cutoff_time:
                    img_file.unlink()
                    deleted_count += 1

            logger.info(f"Deleted {deleted_count} images older than {days_old} days")
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up old images: {e}")
            return deleted_count
