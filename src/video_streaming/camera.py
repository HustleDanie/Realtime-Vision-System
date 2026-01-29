"""
Real-time camera streaming module for industrial computer vision applications.

Supports webcam, video files, and RTSP streams with automatic reconnection,
FPS control, and thread-safe frame reading.
"""

import time
from pathlib import Path
from threading import Thread, Lock
from typing import Optional, Tuple, Generator, Union
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class CameraStream:
    """
    Industrial-grade camera streaming class with robust error handling.
    
    Features:
    - Multiple source types (webcam, video file, RTSP)
    - Automatic reconnection on failure
    - Thread-safe frame reading
    - FPS control and monitoring
    - Frame buffering
    
    Example:
        >>> camera = CameraStream(source=0, fps=30)
        >>> for frame in camera.stream():
        ...     cv2.imshow('Frame', frame)
        ...     if cv2.waitKey(1) & 0xFF == ord('q'):
        ...         break
        >>> camera.release()
    """
    
    def __init__(
        self,
        source: Union[int, str, Path] = 0,
        fps: Optional[int] = None,
        resolution: Optional[Tuple[int, int]] = None,
        buffer_size: int = 1,
        auto_reconnect: bool = True,
        reconnect_delay: float = 2.0,
        backend: Optional[int] = None
    ):
        """
        Initialize camera stream.
        
        Args:
            source: Camera index (0 for default), video file path, or RTSP URL
            fps: Target frames per second (None = max speed)
            resolution: Desired resolution as (width, height)
            buffer_size: Internal buffer size (1 = latest frame only)
            auto_reconnect: Automatically reconnect on stream failure
            reconnect_delay: Seconds to wait before reconnection attempt
            backend: OpenCV VideoCapture backend (e.g., cv2.CAP_DSHOW)
        """
        self.source = source
        self.fps = fps
        self.resolution = resolution
        self.buffer_size = buffer_size
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay
        self.backend = backend
        
        # Threading components
        self.capture: Optional[cv2.VideoCapture] = None
        self.thread: Optional[Thread] = None
        self.lock = Lock()
        self.stopped = False
        self.frame: Optional[np.ndarray] = None
        self.frame_count = 0
        self.read_success = False
        
        # Performance metrics
        self.actual_fps = 0.0
        self.last_frame_time = 0.0
        
        # Initialize capture
        self._initialize_capture()
    
    def _initialize_capture(self) -> bool:
        """Initialize video capture with error handling."""
        try:
            if self.capture is not None:
                self.capture.release()
            
            # Create VideoCapture with optional backend
            if self.backend is not None:
                self.capture = cv2.VideoCapture(self.source, self.backend)
            else:
                self.capture = cv2.VideoCapture(self.source)
            
            if not self.capture.isOpened():
                raise RuntimeError(f"Failed to open source: {self.source}")
            
            # Set buffer size (reduce latency)
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
            
            # Set resolution if specified
            if self.resolution:
                width, height = self.resolution
                self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # Set FPS if specified and source supports it
            if self.fps and isinstance(self.source, int):
                self.capture.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Get actual properties
            actual_width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.capture.get(cv2.CAP_PROP_FPS)
            
            logger.info(
                f"Camera initialized: {self.source} | "
                f"Resolution: {actual_width}x{actual_height} | "
                f"FPS: {actual_fps:.1f}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            return False
    
    def start_threaded(self) -> 'CameraStream':
        """
        Start reading frames in a background thread.
        
        Returns:
            Self for method chaining
        """
        if self.thread is not None and self.thread.is_alive():
            logger.warning("Thread already running")
            return self
        
        self.stopped = False
        self.thread = Thread(target=self._update_frame, daemon=True)
        self.thread.start()
        
        # Wait for first frame
        time.sleep(0.5)
        logger.info("Threaded camera stream started")
        
        return self
    
    def _update_frame(self) -> None:
        """Background thread for continuous frame reading."""
        while not self.stopped:
            if self.capture is None or not self.capture.isOpened():
                if self.auto_reconnect:
                    logger.warning(f"Reconnecting to {self.source}...")
                    time.sleep(self.reconnect_delay)
                    if self._initialize_capture():
                        continue
                    else:
                        break
                else:
                    break
            
            success, frame = self.capture.read()
            
            if success:
                logger.debug(f"Frame captured: #{self.frame_count} | shape={frame.shape} | source={self.source}")
                with self.lock:
                    self.frame = frame
                    self.frame_count += 1
                    self.read_success = True
                    
                    # Calculate actual FPS
                    current_time = time.time()
                    if self.last_frame_time > 0:
                        self.actual_fps = 1.0 / (current_time - self.last_frame_time)
                    self.last_frame_time = current_time
                    logger.debug(f"Frame stored in buffer | FPS: {self.actual_fps:.1f}")
                    
            else:
                self.read_success = False
                if self.auto_reconnect:
                    logger.warning("Frame read failed, attempting reconnect...")
                    time.sleep(self.reconnect_delay)
                    self._initialize_capture()
                else:
                    break
            
            # FPS control
            if self.fps:
                time.sleep(1.0 / self.fps)
    
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read the latest frame (thread-safe).
        
        Returns:
            Tuple of (success, frame)
        """
        if self.thread and self.thread.is_alive():
            # Threaded mode
            with self.lock:
                return self.read_success, self.frame.copy() if self.frame is not None else None
        else:
            # Direct read mode
            if self.capture is None or not self.capture.isOpened():
                return False, None
            return self.capture.read()
    
    def stream(self) -> Generator[np.ndarray, None, None]:
        """
        Generate frames continuously for real-time processing.
        
        Yields:
            numpy.ndarray: Video frame (BGR format)
            
        Example:
            >>> camera = CameraStream(source=0)
            >>> for frame in camera.stream():
            ...     # Process frame
            ...     pass
        """
        frame_interval = 1.0 / self.fps if self.fps else 0
        
        while True:
            start_time = time.time()
            
            if self.capture is None or not self.capture.isOpened():
                if self.auto_reconnect:
                    logger.warning(f"Stream disconnected, reconnecting to {self.source}...")
                    time.sleep(self.reconnect_delay)
                    if not self._initialize_capture():
                        logger.error("Failed to reconnect, stopping stream")
                        break
                    continue
                else:
                    logger.info("Stream ended")
                    break
            
            success, frame = self.capture.read()
            
            if not success:
                if isinstance(self.source, (str, Path)) and not str(self.source).startswith('rtsp'):
                    # Video file ended
                    logger.info("Video file ended")
                    break
                
                if self.auto_reconnect:
                    logger.warning("Failed to read frame, attempting reconnect...")
                    time.sleep(self.reconnect_delay)
                    self._initialize_capture()
                    continue
                else:
                    break
            
            self.frame_count += 1
            
            # Calculate actual FPS
            current_time = time.time()
            if self.last_frame_time > 0:
                self.actual_fps = 1.0 / (current_time - self.last_frame_time)
            self.last_frame_time = current_time
            
            yield frame
            
            # FPS control
            if frame_interval > 0:
                elapsed = time.time() - start_time
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
    
    def get_properties(self) -> dict:
        """
        Get current stream properties.
        
        Returns:
            Dictionary with stream properties
        """
        if self.capture is None:
            return {}
        
        return {
            'width': int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': self.capture.get(cv2.CAP_PROP_FPS),
            'frame_count': self.frame_count,
            'actual_fps': round(self.actual_fps, 2),
            'backend': self.capture.getBackendName(),
            'is_opened': self.capture.isOpened()
        }
    
    def set_property(self, prop_id: int, value: float) -> bool:
        """
        Set capture property.
        
        Args:
            prop_id: OpenCV property ID (e.g., cv2.CAP_PROP_BRIGHTNESS)
            value: Property value
            
        Returns:
            True if successful
        """
        if self.capture is None:
            return False
        return self.capture.set(prop_id, value)
    
    def stop(self) -> None:
        """Stop background thread if running."""
        self.stopped = True
        if self.thread is not None:
            self.thread.join(timeout=2.0)
    
    def release(self) -> None:
        """Release all resources."""
        self.stop()
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        logger.info(f"Camera stream released: {self.frame_count} frames processed")
    
    def __enter__(self) -> 'CameraStream':
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.release()
    
    def __del__(self) -> None:
        """Destructor."""
        self.release()


class MultiCameraStream:
    """
    Manage multiple camera streams simultaneously.
    
    Example:
        >>> sources = [0, 1, 'rtsp://camera.local/stream']
        >>> multi_cam = MultiCameraStream(sources)
        >>> for frames in multi_cam.stream():
        ...     for i, frame in enumerate(frames):
        ...         cv2.imshow(f'Camera {i}', frame)
    """
    
    def __init__(
        self,
        sources: list,
        fps: Optional[int] = None,
        resolution: Optional[Tuple[int, int]] = None
    ):
        """
        Initialize multiple camera streams.
        
        Args:
            sources: List of camera sources (indices, paths, URLs)
            fps: Target FPS for all cameras
            resolution: Desired resolution for all cameras
        """
        self.cameras = [
            CameraStream(source=src, fps=fps, resolution=resolution)
            for src in sources
        ]
        logger.info(f"Initialized {len(self.cameras)} camera streams")
    
    def start_threaded(self) -> 'MultiCameraStream':
        """Start all cameras in threaded mode."""
        for camera in self.cameras:
            camera.start_threaded()
        return self
    
    def read(self) -> list:
        """Read latest frame from all cameras."""
        return [camera.read() for camera in self.cameras]
    
    def stream(self) -> Generator[list, None, None]:
        """
        Generate frames from all cameras simultaneously.
        
        Yields:
            List of frames, one from each camera
        """
        # Start all cameras in threaded mode for synchronization
        self.start_threaded()
        
        while True:
            frames = []
            all_success = True
            
            for camera in self.cameras:
                success, frame = camera.read()
                if success and frame is not None:
                    frames.append(frame)
                else:
                    all_success = False
                    break
            
            if all_success and len(frames) == len(self.cameras):
                yield frames
            else:
                break
    
    def release(self) -> None:
        """Release all camera streams."""
        for camera in self.cameras:
            camera.release()
    
    def __enter__(self) -> 'MultiCameraStream':
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


# Alias for easier import
Camera = CameraStream


if __name__ == "__main__":
    """Demo usage of CameraStream class."""
    
    # Example 1: Basic webcam streaming
    print("Example 1: Webcam streaming (press 'q' to quit)")
    with CameraStream(source=0, fps=30) as camera:
        for frame in camera.stream():
            # Display FPS on frame
            props = camera.get_properties()
            cv2.putText(
                frame, 
                f"FPS: {props['actual_fps']:.1f}", 
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 
                1, 
                (0, 255, 0), 
                2
            )
            
            cv2.imshow('Camera Stream', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cv2.destroyAllWindows()
    
    # Example 2: Video file processing
    print("\nExample 2: Video file processing")
    # camera = CameraStream(source="video.mp4", fps=30)
    # for i, frame in enumerate(camera.stream()):
    #     print(f"Processing frame {i}")
    #     # Process frame...
    #     if i > 100:
    #         break
    # camera.release()
