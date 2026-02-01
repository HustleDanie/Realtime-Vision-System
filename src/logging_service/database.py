"""
Database models and connection management for ML vision logging system.
Provides SQLAlchemy ORM models for prediction logs and database initialization.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class PredictionLog(Base):
    """
    ORM model for storing ML prediction metadata.
    
    Attributes:
        id: Unique prediction identifier
        image_id: Original image filename or identifier
        image_path: Path to saved prediction image on disk
        timestamp: When prediction was made
        model_version: Version of the ML model used
        model_name: Name of the model (e.g., 'yolov8m')
        confidence_score: Confidence of the prediction (0.0-1.0)
        defect_detected: Whether a defect was detected (boolean)
        defect_type: Type of defect detected (if any)
        bounding_boxes: JSON string of bounding boxes
        inference_time_ms: Time taken for inference in milliseconds
        processing_notes: Additional notes about the processing
    """

    __tablename__ = "prediction_logs"

    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Image Information
    image_id = Column(String(255), nullable=False, unique=True, index=True)
    image_path = Column(String(512), nullable=False)

    # Timestamp
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Model Information
    model_version = Column(String(50), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)

    # Prediction Results
    confidence_score = Column(Float, nullable=False)
    defect_detected = Column(Boolean, nullable=False, index=True)
    defect_type = Column(String(100), nullable=True)

    # Detection Details
    bounding_boxes = Column(Text, nullable=True)  # JSON string

    # Performance Metrics
    inference_time_ms = Column(Float, nullable=True)

    # Additional Info
    processing_notes = Column(Text, nullable=True)

    # Indexes for common queries
    __table_args__ = (
        Index("idx_timestamp_defect", "timestamp", "defect_detected"),
        Index("idx_model_version", "model_version"),
        Index("idx_image_id", "image_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<PredictionLog(id={self.id}, image_id='{self.image_id}', "
            f"defect_detected={self.defect_detected}, confidence={self.confidence_score:.3f})>"
        )

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "image_id": self.image_id,
            "image_path": self.image_path,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "model_version": self.model_version,
            "model_name": self.model_name,
            "confidence_score": self.confidence_score,
            "defect_detected": self.defect_detected,
            "defect_type": self.defect_type,
            "bounding_boxes": self.bounding_boxes,
            "inference_time_ms": self.inference_time_ms,
            "processing_notes": self.processing_notes,
        }


class LabelingTask(Base):
    """Images queued for human annotation/triage."""

    __tablename__ = "labeling_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(String(255), nullable=False, unique=True, index=True)
    image_path = Column(String(512), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    confidence_score = Column(Float, nullable=True)
    defect_detected = Column(Boolean, nullable=True)
    model_version = Column(String(50), nullable=True, index=True)
    model_name = Column(String(100), nullable=True)
    reason = Column(String(100), nullable=True)  # "low_confidence", "drift", etc.
    human_label = Column(String(100), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    labeled_at = Column(DateTime, nullable=True)
    extra_data = Column(Text, nullable=True)  # JSON blob with bbox, reason, etc.

    __table_args__ = (
        Index("idx_labeling_status_ts", "status", "timestamp"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "image_id": self.image_id,
            "image_path": self.image_path,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status": self.status,
            "confidence_score": self.confidence_score,
            "defect_detected": self.defect_detected,
            "model_version": self.model_version,
            "model_name": self.model_name,
            "reason": self.reason,
            "human_label": self.human_label,
            "reviewer_notes": self.reviewer_notes,
            "labeled_at": self.labeled_at.isoformat() if self.labeled_at else None,
            "extra_data": self.extra_data,
        }


class ReviewedLabel(Base):
    """Approved labels ready for retraining."""

    __tablename__ = "reviewed_labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(String(255), nullable=False, unique=True, index=True)
    image_path = Column(String(512), nullable=False)
    label = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=True)
    reviewer = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    used_for_training = Column(Boolean, nullable=False, default=False)
    export_path = Column(String(512), nullable=True)

    __table_args__ = (
        Index("idx_reviewed_training", "used_for_training", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "image_id": self.image_id,
            "image_path": self.image_path,
            "label": self.label,
            "confidence": self.confidence,
            "reviewer": self.reviewer,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "used_for_training": self.used_for_training,
            "export_path": self.export_path,
        }


class RetrainingEvent(Base):
    """Track retraining pipeline events."""

    __tablename__ = "retraining_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100), nullable=False, unique=True, index=True)
    triggered_by = Column(String(50), nullable=False)  # "drift" or "new_labels"
    drift_score = Column(Float, nullable=True)
    new_labels_count = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="started")  # started, running, completed, failed
    model_version = Column(String(50), nullable=True)
    previous_model_version = Column(String(50), nullable=True)
    new_model_version = Column(String(50), nullable=True)
    improvement_metrics = Column(Text, nullable=True)  # JSON with new vs old metrics
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_retraining_status", "status", "started_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_id": self.event_id,
            "triggered_by": self.triggered_by,
            "drift_score": self.drift_score,
            "new_labels_count": self.new_labels_count,
            "status": self.status,
            "model_version": self.model_version,
            "previous_model_version": self.previous_model_version,
            "new_model_version": self.new_model_version,
            "improvement_metrics": self.improvement_metrics,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


class DatabaseConnection:
    """
    Manages database connection and session creation.
    Supports SQLite, PostgreSQL, and MySQL.
    """

    def __init__(
        self,
        db_url: str = "sqlite:///./vision_logs.db",
        echo: bool = False,
        pool_size: int = 10,
        max_overflow: int = 20,
    ):
        """
        Initialize database connection.

        Args:
            db_url: Database URL (e.g., 'sqlite:///vision_logs.db',
                   'postgresql://user:pass@localhost/dbname')
            echo: Whether to echo SQL statements
            pool_size: Connection pool size (for non-SQLite)
            max_overflow: Max overflow size for connection pool
        """
        self.db_url = db_url
        self.echo = echo

        # Create engine with appropriate configuration
        if db_url.startswith("sqlite"):
            self.engine = create_engine(
                db_url,
                echo=echo,
                connect_args={"check_same_thread": False},
            )
        else:
            self.engine = create_engine(
                db_url,
                echo=echo,
                pool_size=pool_size,
                max_overflow=max_overflow,
            )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        logger.info(f"Database connection initialized: {db_url}")

    def init_db(self) -> None:
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def close(self) -> None:
        """Close all connections in the pool."""
        self.engine.dispose()
        logger.info("Database connection closed")

    def health_check(self) -> bool:
        """
        Check if database connection is healthy.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Context manager for session handling
class SessionManager:
    """Context manager for database session handling."""

    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection
        self.session: Optional[Session] = None

    def __enter__(self) -> Session:
        self.session = self.db_connection.get_session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.session:
            self.session.close()
