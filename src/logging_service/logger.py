"""
Main logging service for ML vision system.
Coordinates image storage and database logging of predictions.
"""

from datetime import datetime, timedelta
import numpy as np
from typing import Optional, Dict, Any, List
import json
import logging
from pathlib import Path

from sqlalchemy import func

from .database import DatabaseConnection, PredictionLog, SessionManager, LabelingTask
from .storage import ImageStorage
from .config import LoggingServiceConfig


class VisionLogger:
    """
    Comprehensive logging service for ML vision predictions.

    Handles:
    - Saving prediction images to disk with organized directory structure
    - Logging prediction metadata to SQL database
    - Querying and retrieving logged predictions
    - Maintaining data consistency and integrity
    """

    def __init__(self, config: Optional[LoggingServiceConfig] = None):
        """
        Initialize logging service.

        Args:
            config: LoggingServiceConfig instance (uses defaults if not provided)
        """
        if config is None:
            config = LoggingServiceConfig()

        self.config = config
        self.logger = self._setup_logging()

        # Initialize components
        self.db_connection = DatabaseConnection(
            db_url=config.database.url,
            echo=config.database.echo,
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
        )

        self.storage = ImageStorage(
            base_path=config.storage.base_path,
            organize_by_date=config.storage.organize_by_date,
            organize_by_result=config.storage.organize_by_result,
        )

        # Initialize database
        if config.database.auto_migrate:
            self.db_connection.init_db()

        self.logger.info("VisionLogger initialized successfully")

    def _setup_logging(self) -> logging.Logger:
        """
        Setup Python logging configuration.

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(__name__)
        logger.setLevel(self.config.logging.log_level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.config.logging.log_level)
        formatter = logging.Formatter(self.config.logging.log_format)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (if configured)
        if self.config.logging.log_file:
            log_path = Path(self.config.logging.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            from logging.handlers import RotatingFileHandler

            file_handler = RotatingFileHandler(
                self.config.logging.log_file,
                maxBytes=self.config.logging.max_bytes,
                backupCount=self.config.logging.backup_count,
            )
            file_handler.setLevel(self.config.logging.log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def log_prediction(
        self,
        image,
        image_id: str,
        confidence: float,
        defect_detected: bool,
        timestamp: Optional[datetime] = None,
        defect_type: Optional[str] = None,
        bounding_boxes: Optional[List[Dict[str, Any]]] = None,
        inference_time_ms: Optional[float] = None,
        processing_notes: Optional[str] = None,
    ) -> int:
        """
        Log a complete prediction (image + metadata).

        Args:
            image: OpenCV image (numpy array)
            image_id: Unique identifier for the image
            confidence: Confidence score (0.0-1.0)
            defect_detected: Whether defect was detected
            timestamp: Prediction timestamp (defaults to now)
            defect_type: Type of defect detected (if any)
            bounding_boxes: List of bounding box dicts with keys:
                           {x, y, width, height, confidence, class}
            inference_time_ms: Time taken for inference
            processing_notes: Additional notes

        Returns:
            ID of the logged prediction

        Raises:
            ValueError: If inputs are invalid
            IOError: If image save fails
        """
        # Validate inputs
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {confidence}")

        if timestamp is None:
            timestamp = datetime.utcnow()

        try:
            # Save image to disk
            image_path = self.storage.save_image(
                image=image,
                image_id=image_id,
                timestamp=timestamp,
                defect_detected=defect_detected,
                quality=self.config.storage.image_quality,
            )

            # Prepare bounding boxes as JSON
            bbox_json = json.dumps(bounding_boxes) if bounding_boxes else None

            # Create database record
            with SessionManager(self.db_connection) as session:
                log_entry = PredictionLog(
                    image_id=image_id,
                    image_path=image_path,
                    timestamp=timestamp,
                    model_version=self.config.model_version,
                    model_name=self.config.model_name,
                    confidence_score=confidence,
                    defect_detected=defect_detected,
                    defect_type=defect_type,
                    bounding_boxes=bbox_json,
                    inference_time_ms=inference_time_ms,
                    processing_notes=processing_notes,
                )

                session.add(log_entry)
                session.commit()

                log_id = log_entry.id
                self.logger.info(
                    f"Prediction logged: id={log_id}, image_id={image_id}, "
                    f"defect={defect_detected}, confidence={confidence:.3f}"
                )

                return log_id

        except Exception as e:
            self.logger.error(f"Error logging prediction for {image_id}: {e}")
            raise

    def get_prediction(self, prediction_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a prediction log by ID.

        Args:
            prediction_id: ID of the prediction

        Returns:
            Dictionary with prediction data or None if not found
        """
        try:
            with SessionManager(self.db_connection) as session:
                log_entry = session.query(PredictionLog).filter(
                    PredictionLog.id == prediction_id
                ).first()

                if log_entry:
                    return log_entry.to_dict()
                return None

        except Exception as e:
            self.logger.error(f"Error retrieving prediction {prediction_id}: {e}")
            return None

    def get_predictions_by_date(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all predictions within a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of prediction dictionaries
        """
        try:
            with SessionManager(self.db_connection) as session:
                logs = session.query(PredictionLog).filter(
                    PredictionLog.timestamp >= start_date,
                    PredictionLog.timestamp <= end_date,
                ).order_by(PredictionLog.timestamp.desc()).all()

                return [log.to_dict() for log in logs]

        except Exception as e:
            self.logger.error(f"Error retrieving predictions by date: {e}")
            return []

    def get_defect_predictions(
        self,
        defect_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all defect predictions.

        Args:
            defect_type: Filter by specific defect type (optional)
            limit: Maximum number of results

        Returns:
            List of defect prediction dictionaries
        """
        try:
            with SessionManager(self.db_connection) as session:
                query = session.query(PredictionLog).filter(
                    PredictionLog.defect_detected == True
                )

                if defect_type:
                    query = query.filter(
                        PredictionLog.defect_type == defect_type
                    )

                logs = query.order_by(
                    PredictionLog.timestamp.desc()
                ).limit(limit).all()

                return [log.to_dict() for log in logs]

        except Exception as e:
            self.logger.error(f"Error retrieving defect predictions: {e}")
            return []

    def get_predictions_by_model(
        self,
        model_version: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve predictions made by a specific model version.

        Args:
            model_version: Model version to filter by
            limit: Maximum number of results

        Returns:
            List of prediction dictionaries
        """
        try:
            with SessionManager(self.db_connection) as session:
                logs = session.query(PredictionLog).filter(
                    PredictionLog.model_version == model_version
                ).order_by(PredictionLog.timestamp.desc()).limit(limit).all()

                return [log.to_dict() for log in logs]

        except Exception as e:
            self.logger.error(
                f"Error retrieving predictions for model {model_version}: {e}"
            )
            return []

    def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        rolling_window_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics about logged predictions.

        Args:
            start_date: Filter from this date (optional)
            end_date: Filter until this date (optional)
            rolling_window_minutes: Compute rolling averages over the last N minutes (optional)

        Returns:
            Dictionary with statistics
        """
        try:
            with SessionManager(self.db_connection) as session:
                query = session.query(PredictionLog)

                if start_date:
                    query = query.filter(PredictionLog.timestamp >= start_date)
                if end_date:
                    query = query.filter(PredictionLog.timestamp <= end_date)

                def aggregate(q) -> Dict[str, Any]:
                    total = q.count()
                    defects = q.filter(PredictionLog.defect_detected == True).count()
                    no_defects = q.filter(PredictionLog.defect_detected == False).count()
                    avg_confidence = (
                        q.with_entities(func.avg(PredictionLog.confidence_score)).scalar() or 0.0
                    )
                    return {
                        "total_predictions": total,
                        "defects_found": defects,
                        "no_defects": no_defects,
                        "defect_rate": (defects / total * 100) if total > 0 else 0,
                        "average_confidence": float(avg_confidence),
                    }

                stats = aggregate(query)

                # Defect types distribution (overall)
                defect_types = {}
                defect_logs = (
                    query.filter(PredictionLog.defect_detected == True)
                    .all()
                )
                for log in defect_logs:
                    dtype = log.defect_type or "unknown"
                    defect_types[dtype] = defect_types.get(dtype, 0) + 1
                stats["defect_types"] = defect_types

                # Rolling window statistics
                if rolling_window_minutes and rolling_window_minutes > 0:
                    window_start = datetime.utcnow() - timedelta(minutes=rolling_window_minutes)
                    rolling_query = query.filter(PredictionLog.timestamp >= window_start)
                    rolling_stats = aggregate(rolling_query)
                    rolling_stats["window_minutes"] = rolling_window_minutes
                    rolling_stats["detection_frequency_per_min"] = (
                        rolling_stats["total_predictions"] / rolling_window_minutes
                        if rolling_window_minutes > 0
                        else 0
                    )
                    stats.update(
                        {
                            "rolling": rolling_stats,
                            "rolling_defect_rate": rolling_stats["defect_rate"],
                            "rolling_average_confidence": rolling_stats["average_confidence"],
                            "rolling_detection_frequency_per_min": rolling_stats[
                                "detection_frequency_per_min"
                            ],
                        }
                    )

                storage_stats = self.storage.get_storage_stats()
                stats["storage"] = storage_stats

                self.logger.info(f"Generated statistics: {stats}")
                return stats

        except Exception as e:
            self.logger.error(f"Error generating statistics: {e}")
            return {}

    def enqueue_for_labeling(
        self,
        image,
        image_id: str,
        confidence: Optional[float] = None,
        defect_detected: Optional[bool] = None,
        defect_type: Optional[str] = None,
        bounding_boxes: Optional[List[Dict[str, Any]]] = None,
        reason: str = "uncertain",
        timestamp: Optional[datetime] = None,
    ) -> int:
        """Persist an uncertain prediction for human review."""

        if timestamp is None:
            timestamp = datetime.utcnow()

        image_path = self.storage.save_labeling_image(
            image=image,
            image_id=image_id,
            timestamp=timestamp,
            quality=self.config.storage.image_quality,
        )

        metadata = {
            "reason": reason,
            "defect_type": defect_type,
            "bounding_boxes": bounding_boxes,
            "model_version": self.config.model_version,
            "model_name": self.config.model_name,
        }

        try:
            with SessionManager(self.db_connection) as session:
                task = LabelingTask(
                    image_id=image_id,
                    image_path=image_path,
                    timestamp=timestamp,
                    status="pending",
                    confidence_score=confidence,
                    defect_detected=defect_detected,
                    model_version=self.config.model_version,
                    model_name=self.config.model_name,
                    metadata=json.dumps(metadata),
                )
                session.add(task)
                session.commit()
                self.logger.info(
                    f"Queued for labeling: id={task.id}, image_id={image_id}, reason={reason}"
                )
                return task.id
        except Exception as e:
            self.logger.error(f"Error enqueuing image {image_id} for labeling: {e}")
            raise

    def detect_model_degradation(
        self,
        baseline_hours: int = 24,
        recent_minutes: int = 60,
        defect_rate_threshold_pct: float = 5.0,
        confidence_mean_drop: float = 0.05,
        confidence_p10_drop: float = 0.1,
    ) -> Dict[str, Any]:
        """Heuristic detector for potential model degradation.

        Compares a recent window vs a baseline window and flags when:
        - Defect rate increases by more than `defect_rate_threshold_pct` points
        - Average confidence drops by more than `confidence_mean_drop`
        - P10 confidence drops by more than `confidence_p10_drop`

        Returns a dictionary with metrics and a `degraded` flag.
        """

        now = datetime.utcnow()
        baseline_start = now - timedelta(hours=baseline_hours)
        recent_start = now - timedelta(minutes=recent_minutes)

        def window_metrics(session, start_ts):
            q = session.query(PredictionLog).filter(PredictionLog.timestamp >= start_ts)
            total = q.count()
            defects = q.filter(PredictionLog.defect_detected == True).count()
            defect_rate = (defects / total * 100.0) if total > 0 else 0.0
            confs = [row[0] for row in q.with_entities(PredictionLog.confidence_score).all()]
            if confs:
                conf_mean = float(np.mean(confs))
                conf_p10 = float(np.percentile(confs, 10))
                conf_p90 = float(np.percentile(confs, 90))
            else:
                conf_mean = conf_p10 = conf_p90 = 0.0
            return {
                "total": total,
                "defects": defects,
                "defect_rate": defect_rate,
                "confidence_mean": conf_mean,
                "confidence_p10": conf_p10,
                "confidence_p90": conf_p90,
            }

        try:
            with SessionManager(self.db_connection) as session:
                baseline = window_metrics(session, baseline_start)
                recent = window_metrics(session, recent_start)

                defect_rate_delta = recent["defect_rate"] - baseline["defect_rate"]
                conf_mean_drop = baseline["confidence_mean"] - recent["confidence_mean"]
                conf_p10_drop = baseline["confidence_p10"] - recent["confidence_p10"]

                degraded_reasons = []
                if defect_rate_delta > defect_rate_threshold_pct:
                    degraded_reasons.append(
                        f"defect_rate up {defect_rate_delta:.2f}pp (> {defect_rate_threshold_pct}pp)"
                    )
                if conf_mean_drop > confidence_mean_drop:
                    degraded_reasons.append(
                        f"confidence_mean down {conf_mean_drop:.3f} (> {confidence_mean_drop})"
                    )
                if conf_p10_drop > confidence_p10_drop:
                    degraded_reasons.append(
                        f"confidence_p10 down {conf_p10_drop:.3f} (> {confidence_p10_drop})"
                    )

                degraded = len(degraded_reasons) > 0

                result = {
                    "baseline_window_hours": baseline_hours,
                    "recent_window_minutes": recent_minutes,
                    "baseline": baseline,
                    "recent": recent,
                    "defect_rate_delta_pp": defect_rate_delta,
                    "confidence_mean_drop": conf_mean_drop,
                    "confidence_p10_drop": conf_p10_drop,
                    "thresholds": {
                        "defect_rate_threshold_pp": defect_rate_threshold_pct,
                        "confidence_mean_drop": confidence_mean_drop,
                        "confidence_p10_drop": confidence_p10_drop,
                    },
                    "degraded": degraded,
                    "reasons": degraded_reasons,
                }

                if degraded:
                    self.logger.warning(f"Model degradation suspected: {degraded_reasons}")
                else:
                    self.logger.info("Model health OK (no drift over thresholds)")

                return result

        except Exception as e:
            self.logger.error(f"Error detecting model degradation: {e}")
            return {"error": str(e), "degraded": False}

    def export_predictions(
        self,
        output_file: str,
        defect_only: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """
        Export predictions to JSON file.

        Args:
            output_file: Path to output JSON file
            defect_only: Only export defect predictions
            start_date: Filter from this date (optional)
            end_date: Filter until this date (optional)

        Returns:
            Number of predictions exported
        """
        try:
            with SessionManager(self.db_connection) as session:
                query = session.query(PredictionLog)

                if defect_only:
                    query = query.filter(PredictionLog.defect_detected == True)
                if start_date:
                    query = query.filter(PredictionLog.timestamp >= start_date)
                if end_date:
                    query = query.filter(PredictionLog.timestamp <= end_date)

                logs = query.all()
                predictions = [log.to_dict() for log in logs]

                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "w") as f:
                    json.dump(predictions, f, indent=2, default=str)

                self.logger.info(
                    f"Exported {len(predictions)} predictions to {output_file}"
                )
                return len(predictions)

        except Exception as e:
            self.logger.error(f"Error exporting predictions: {e}")
            return 0

    def health_check(self) -> Dict[str, bool]:
        """
        Perform health check on logging service.

        Returns:
            Dictionary with health status
        """
        return {
            "database": self.db_connection.health_check(),
            "storage": self.storage.base_path.exists(),
        }

    def cleanup(self) -> None:
        """
        Close database connections and cleanup resources.
        """
        self.db_connection.close()
        self.logger.info("VisionLogger cleanup completed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
