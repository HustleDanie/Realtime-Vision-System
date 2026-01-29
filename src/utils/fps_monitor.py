"""FPS monitoring and performance tracking utilities."""

import time
import numpy as np
from collections import deque


class FPSMonitor:
    """Monitor and calculate FPS with detailed metrics."""
    
    def __init__(self, window_size=30):
        """
        Initialize FPS monitor.
        
        Args:
            window_size: Number of frames to average over
        """
        self.window_size = window_size
        self.frame_times = deque(maxlen=window_size)
        self.inference_times = deque(maxlen=window_size)
        self.total_frames = 0
        self.start_time = time.time()
    
    def update(self, frame_time, inference_time):
        """
        Update with frame timing information.
        
        Args:
            frame_time: Total time to process frame (seconds)
            inference_time: Time spent in YOLO inference (seconds)
        """
        self.frame_times.append(frame_time)
        self.inference_times.append(inference_time)
        self.total_frames += 1
    
    @property
    def fps(self):
        """Current FPS (average over window)."""
        if not self.frame_times:
            return 0.0
        return 1.0 / np.mean(self.frame_times)
    
    @property
    def avg_inference_fps(self):
        """Average FPS if only doing inference (no I/O)."""
        if not self.inference_times:
            return 0.0
        return 1.0 / np.mean(self.inference_times)
    
    @property
    def min_fps(self):
        """Minimum FPS in window."""
        if not self.frame_times:
            return 0.0
        return 1.0 / max(self.frame_times)
    
    @property
    def max_fps(self):
        """Maximum FPS in window."""
        if not self.frame_times:
            return 0.0
        return 1.0 / min(self.frame_times)
    
    @property
    def avg_frame_time(self):
        """Average frame processing time (ms)."""
        if not self.frame_times:
            return 0.0
        return np.mean(self.frame_times) * 1000
    
    @property
    def avg_inference_time(self):
        """Average inference time (ms)."""
        if not self.inference_times:
            return 0.0
        return np.mean(self.inference_times) * 1000
    
    @property
    def total_time_elapsed(self):
        """Total elapsed time (seconds)."""
        return time.time() - self.start_time
    
    @property
    def overall_fps(self):
        """Overall FPS since start."""
        elapsed = self.total_time_elapsed
        if elapsed < 0.1:
            return 0.0
        return self.total_frames / elapsed
    
    def get_summary(self):
        """Get summary statistics."""
        return {
            'fps': self.fps,
            'avg_fps': self.overall_fps,
            'min_fps': self.min_fps,
            'max_fps': self.max_fps,
            'inference_fps': self.avg_inference_fps,
            'frame_time_ms': self.avg_frame_time,
            'inference_time_ms': self.avg_inference_time,
            'total_frames': self.total_frames,
            'elapsed_s': self.total_time_elapsed
        }
