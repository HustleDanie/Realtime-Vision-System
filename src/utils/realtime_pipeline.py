"""Real-time detection pipeline orchestration."""

import cv2
import logging
import time
from datetime import datetime
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

from src.video_streaming import Camera
from src.preprocessing import ImageProcessor
from src.yolo_inference import YOLODetector, detect_objects
from src.utils.visualization import (
    draw_bounding_boxes,
    draw_detection_info,
    create_color_palette
)
from src.utils.fps_monitor import FPSMonitor
from src.utils.fps_renderer import FPSRenderer
from src.logging_service import VisionLogger, LoggingServiceConfig


logger = logging.getLogger(__name__)


class DetectionPipeline:
    """
    Orchestrates the complete real-time detection pipeline.
    
    Combines:
    - Camera streaming
    - Image preprocessing
    - YOLO inference
    - Visualization
    - Performance monitoring
    """
    
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        confidence_threshold: float = 0.5,
        device: str = "auto",
        model_version: Optional[str] = None,
        enable_logging: bool = False,
        log_defects_only: bool = True,
        logging_config: Optional[LoggingServiceConfig] = None,
    ):
        """
        Initialize pipeline.
        
        Args:
            model_path: Path to YOLO model
            confidence_threshold: Detection confidence threshold
            device: "auto", "gpu", or "cpu"
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.model_version = model_version or Path(model_path).stem
        self.model_name = Path(model_path).stem
        self.enable_logging = enable_logging
        self.log_defects_only = log_defects_only
        self._logging_config = logging_config
        
        # Components
        self.camera: Optional[Camera] = None
        self.preprocessor: Optional[ImageProcessor] = None
        self.detector: Optional[YOLODetector] = None
        self.logger_service: Optional[VisionLogger] = None
        
        # Monitoring
        self.fps_monitor = FPSMonitor(window_size=30)
        self.fps_renderer = FPSRenderer()
        
        # State
        self.paused = False
        self.frame_count = 0
        self.class_colors: Dict[str, Tuple[int, int, int]] = {}
        
        logger.info(
            "Pipeline initialized | model=%s | version=%s | logging=%s",
            self.model_name,
            self.model_version,
            "on" if self.enable_logging else "off",
        )
    
    def setup(self) -> bool:
        """
        Initialize all pipeline components.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            logger.info("Setting up pipeline components...")
            
            # Initialize camera
            logger.info("Initializing camera...")
            self.camera = Camera(source=0, fps=30)
            
            # Initialize preprocessor
            logger.info("Initializing preprocessor...")
            self.preprocessor = ImageProcessor(
                target_size=(640, 480),
                normalization_type="0-1"
            )
            
            # Initialize detector
            logger.info(f"Loading YOLO model: {self.model_path}")
            self.detector = YOLODetector(
                model_path=self.model_path,
                device=self.device,
                confidence_threshold=self.confidence_threshold
            )
            self.detector.load_model()
            
            # Warmup model
            logger.info("Warming up model...")
            self.detector.warmup()
            
            # Generate class colors
            logger.info("Generating class colors...")
            colors = create_color_palette(80, colormap="hsv")
            if hasattr(self.detector.model, 'names'):
                for class_id, class_name in self.detector.model.names.items():
                    self.class_colors[class_name] = colors[class_id % len(colors)]

            # Initialize logging service (optional)
            if self.enable_logging:
                cfg = self._logging_config or LoggingServiceConfig()
                # Ensure model identifiers propagate to logs
                cfg.model_version = cfg.model_version or self.model_version
                cfg.model_name = cfg.model_name or self.model_name
                self.logger_service = VisionLogger(cfg)
                logger.info(
                    "Logging enabled | model=%s | version=%s",
                    cfg.model_name,
                    cfg.model_version,
                )
            
            logger.info("✅ Pipeline setup complete!")
            return True
        
        except Exception as e:
            logger.error(f"Setup failed: {e}", exc_info=True)
            return False
    
    def process_frame(self, frame) -> Tuple[Any, dict, float]:
        """
        Process a single frame through the pipeline.
        
        Args:
            frame: Input frame
            
        Returns:
            Tuple of (processed_frame, detection_results, inference_time)
        """
        start_time = time.time()
        
        # Preprocess
        original, processed = self.preprocessor.process(frame)
        
        # Detect objects
        results = detect_objects(
            original,
            self.detector,
            return_format="dict"
        )
        
        inference_time = time.time() - start_time
        
        return original, results, inference_time
    
    def draw_frame(self, frame, results: dict) -> np.ndarray:
        """
        Draw detections on frame.
        
        Args:
            frame: Input frame
            results: Detection results dictionary
            
        Returns:
            Frame with drawn detections
        """
        if results['num_detections'] == 0:
            return frame
        
        # Get colors for detected classes
        box_colors = []
        for cls in results['classes']:
            box_colors.append(self.class_colors.get(cls, (0, 255, 0)))
        
        # Draw bounding boxes
        frame = draw_bounding_boxes(
            frame,
            results['boxes'],
            results['classes'],
            results['confidences'],
            colors=box_colors,
            thickness=2,
            font_scale=0.5,
            show_confidence=True
        )
        
        return frame
    
    def add_overlays(self, frame, results: dict) -> np.ndarray:
        """
        Add all overlay information to frame.
        
        Args:
            frame: Input frame
            results: Detection results dictionary
            
        Returns:
            Frame with overlays
        """
        stats = self.fps_monitor.get_summary()
        
        # FPS overlays
        frame = self.fps_renderer.render_all(
            frame,
            fps=stats['fps'],
            stats=stats,
            frame_times=list(self.fps_monitor.frame_times)
        )
        
        # Info panel
        info = [
            f"Objects: {results['num_detections']}",
            f"Model: {Path(self.model_path).stem}",
            f"Device: {self.detector.device.type.upper()}",
            f"Status: {'PAUSED' if self.paused else 'RUNNING'}"
        ]
        
        frame = draw_detection_info(
            frame,
            info,
            position=(10, 90),
            font_scale=0.5,
            color=(0, 255, 0),
            background=True,
            thickness=1
        )
        
        # Help text
        help_text = "Q:Quit P:Pause C:Conf F:FPS I:Info G:Graph D:Detail S:Save"
        cv2.putText(
            frame, help_text,
            (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            (200, 200, 200),
            1,
            cv2.LINE_AA
        )
        
        return frame

    def _format_bounding_boxes(self, results: dict) -> List[Dict[str, Any]]:
        """
        Convert detection results into bounding box dictionaries for logging.
        """
        boxes = results.get('boxes', [])
        classes = results.get('classes', [])
        confidences = results.get('confidences', [])

        formatted: List[Dict[str, Any]] = []
        for box, cls, conf in zip(boxes, classes, confidences):
            x1, y1, x2, y2 = box
            formatted.append({
                "x": float(x1),
                "y": float(y1),
                "width": float(x2 - x1),
                "height": float(y2 - y1),
                "confidence": float(conf),
                "class": cls,
            })
        return formatted

    def _log_prediction_if_enabled(
        self,
        frame: np.ndarray,
        results: dict,
        inference_time: float,
    ) -> None:
        """
        Persist prediction (image + metadata) when logging is enabled.
        """
        if not self.logger_service:
            return

        has_defect = results.get('num_detections', 0) > 0
        if self.log_defects_only and not has_defect:
            return

        timestamp = datetime.utcnow()
        image_id = f"frame_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}_{self.frame_count:06d}"

        bounding_boxes = self._format_bounding_boxes(results)

        defect_type = results['classes'][0] if has_defect and results.get('classes') else None

        # inference_time is in seconds; convert to milliseconds
        inference_ms = inference_time * 1000.0

        try:
            self.logger_service.log_prediction(
                image=frame,
                image_id=image_id,
                confidence=max(results.get('confidences', [0.0]) or [0.0]),
                defect_detected=has_defect,
                defect_type=defect_type,
                bounding_boxes=bounding_boxes if bounding_boxes else None,
                inference_time_ms=inference_ms,
                processing_notes=f"Detections={results.get('num_detections', 0)}",
            )
        except Exception:
            logger.exception("Failed to log prediction for %s", image_id)
    
    def handle_keyboard_input(self, key: int) -> bool:
        """
        Handle keyboard input.
        
        Args:
            key: Pressed key code
            
        Returns:
            True if should continue, False if should quit
        """
        if key == ord('q'):
            logger.info("Quit requested")
            return False
        elif key == ord('p'):
            self.paused = not self.paused
            logger.info(f"{'Paused' if self.paused else 'Resumed'}")
        elif key == ord('c'):
            # Toggle confidence (affects visualization)
            logger.info("Confidence toggle")
        elif key == ord('f'):
            self.fps_renderer.show_main = not self.fps_renderer.show_main
            logger.info(f"FPS display: {'ON' if self.fps_renderer.show_main else 'OFF'}")
        elif key == ord('i'):
            logger.info("Info panel toggle")
        elif key == ord('g'):
            self.fps_renderer.show_graph = not self.fps_renderer.show_graph
            logger.info(f"FPS graph: {'ON' if self.fps_renderer.show_graph else 'OFF'}")
        elif key == ord('d'):
            self.fps_renderer.show_detailed = not self.fps_renderer.show_detailed
            logger.info(f"Detailed stats: {'ON' if self.fps_renderer.show_detailed else 'OFF'}")
        elif key == ord('s'):
            logger.info("Save frame requested")
        
        return True
    
    def run(self, output_dir: str = "output/detections") -> None:
        """
        Run the detection pipeline.
        
        Args:
            output_dir: Directory to save frames
        """
        if not self.setup():
            logger.error("Failed to setup pipeline")
            return
        
        logger.info("Starting real-time detection. Press 'q' to quit")
        
        # Setup display
        window_name = "Real-time Object Detection"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)
        
        # Setup output directory
        save_dir = Path(output_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            for frame in self.camera.stream():
                # Handle paused state
                if self.paused:
                    cv2.imshow(window_name, frame)
                    key = cv2.waitKey(1) & 0xFF
                    if not self.handle_keyboard_input(key):
                        break
                    continue
                
                # Process frame
                frame_start = time.time()
                original, results, inference_time = self.process_frame(frame)
                
                # Draw detections
                output = self.draw_frame(original.copy(), results)
                
                # Update monitoring
                frame_time = time.time() - frame_start
                self.fps_monitor.update(frame_time, inference_time)
                
                # Add overlays
                output = self.add_overlays(output, results)

                # Persist prediction with model version metadata if enabled
                self._log_prediction_if_enabled(output, results, inference_time)
                
                # Display
                cv2.imshow(window_name, output)
                
                # Handle input
                key = cv2.waitKey(1) & 0xFF
                if not self.handle_keyboard_input(key):
                    break
                
                # Save frame if requested
                if key == ord('s'):
                    save_path = save_dir / f"frame_{int(time.time()*1000)}.jpg"
                    cv2.imwrite(str(save_path), output)
                    logger.info(f"Frame saved: {save_path}")
                
                self.frame_count += 1
                
                # Log progress periodically
                if self.frame_count % 300 == 0:
                    stats = self.fps_monitor.get_summary()
                    logger.info(
                        f"Progress: {self.frame_count} frames | "
                        f"FPS: {stats['fps']:.1f} (Avg: {stats['avg_fps']:.1f}) | "
                        f"Inference: {stats['inference_time_ms']:.1f}ms"
                    )
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error during execution: {e}", exc_info=True)
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """Clean up resources and print statistics."""
        logger.info("Cleaning up...")
        
        if self.camera:
            self.camera.release()
        
        if self.logger_service:
            self.logger_service.cleanup()
        
        cv2.destroyAllWindows()
        
        # Print statistics
        stats = self.fps_monitor.get_summary()
        logger.info("\n" + "="*70)
        logger.info("PERFORMANCE STATISTICS")
        logger.info("="*70)
        logger.info(f"Total frames processed: {stats['total_frames']}")
        logger.info(f"Total time elapsed: {stats['elapsed_s']:.1f}s")
        logger.info(f"\nFPS Metrics:")
        logger.info(f"  Current FPS: {stats['fps']:.1f}")
        logger.info(f"  Average FPS: {stats['avg_fps']:.1f}")
        logger.info(f"  Min FPS: {stats['min_fps']:.1f}")
        logger.info(f"  Max FPS: {stats['max_fps']:.1f}")
        logger.info(f"\nTiming Metrics:")
        logger.info(f"  Avg frame time: {stats['frame_time_ms']:.1f}ms")
        logger.info(f"  Avg inference time: {stats['inference_time_ms']:.1f}ms")
        logger.info(f"  Inference FPS: {stats['inference_fps']:.1f}")
        logger.info("="*70)
        logger.info("Pipeline stopped")
