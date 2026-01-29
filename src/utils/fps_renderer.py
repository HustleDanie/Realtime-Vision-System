"""FPS visualization and overlay rendering."""

import cv2
import numpy as np
from typing import Optional, List


class FPSRenderer:
    """Renders FPS and performance metrics on video frames."""
    
    def __init__(self):
        """Initialize FPS renderer."""
        self.show_main = True
        self.show_detailed = False
        self.show_graph = False
    
    def render_main_fps(self, frame, fps: float) -> np.ndarray:
        """
        Render main FPS counter.
        
        Args:
            frame: Input frame
            fps: FPS value to display
            
        Returns:
            Frame with FPS overlay
        """
        if not self.show_main:
            return frame
        
        fps_text = f"{fps:.1f} FPS"
        cv2.putText(
            frame, fps_text,
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 0),
            2,
            cv2.LINE_AA
        )
        
        return frame
    
    def render_detailed_stats(self, frame, stats: dict) -> np.ndarray:
        """
        Render detailed performance statistics.
        
        Args:
            frame: Input frame
            stats: Statistics dictionary from FPSMonitor.get_summary()
            
        Returns:
            Frame with stats overlay
        """
        if not self.show_detailed:
            return frame
        
        detail_text = [
            f"Avg: {stats['avg_fps']:.1f} | Min: {stats['min_fps']:.1f} | Max: {stats['max_fps']:.1f}",
            f"Frame: {stats['frame_time_ms']:.1f}ms | Inf: {stats['inference_time_ms']:.1f}ms",
        ]
        
        y_pos = 70
        for text in detail_text:
            cv2.putText(
                frame, text,
                (10, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (200, 200, 0),
                1,
                cv2.LINE_AA
            )
            y_pos += 25
        
        return frame
    
    def render_fps_graph(self, frame, frame_times: List[float]) -> np.ndarray:
        """
        Render FPS history graph.
        
        Args:
            frame: Input frame
            frame_times: List of frame times (seconds)
            
        Returns:
            Frame with FPS graph overlay
        """
        if not self.show_graph or len(frame_times) < 2:
            return frame
        
        graph_width = 200
        graph_height = 100
        graph_x = frame.shape[1] - graph_width - 10
        graph_y = 10
        
        # Draw background
        cv2.rectangle(
            frame,
            (graph_x, graph_y),
            (graph_x + graph_width, graph_y + graph_height),
            (50, 50, 50),
            -1
        )
        
        # Draw border
        cv2.rectangle(
            frame,
            (graph_x, graph_y),
            (graph_x + graph_width, graph_y + graph_height),
            (100, 100, 100),
            1
        )
        
        # Calculate FPS values
        fps_values = [1.0 / ft if ft > 0 else 0 for ft in frame_times]
        
        if fps_values:
            max_fps = max(fps_values) * 1.2 if max(fps_values) > 0 else 30
            
            # Draw FPS line graph
            for i in range(len(fps_values) - 1):
                y1 = graph_y + graph_height - int((fps_values[i] / max_fps) * (graph_height - 5))
                y2 = graph_y + graph_height - int((fps_values[i + 1] / max_fps) * (graph_height - 5))
                
                x1 = graph_x + int((i / len(fps_values)) * (graph_width - 5))
                x2 = graph_x + int(((i + 1) / len(fps_values)) * (graph_width - 5))
                
                # Color based on performance
                if fps_values[i + 1] < 15:
                    color = (0, 0, 255)  # Red - low FPS
                elif fps_values[i + 1] < 25:
                    color = (0, 165, 255)  # Orange - medium
                else:
                    color = (0, 255, 0)  # Green - good
                
                cv2.line(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw max line reference
            cv2.line(
                frame,
                (graph_x + 2, graph_y + 5),
                (graph_x + graph_width - 2, graph_y + 5),
                (100, 100, 100),
                1
            )
            cv2.putText(
                frame, f"{max_fps:.0f}",
                (graph_x + graph_width - 35, graph_y + 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (150, 150, 150),
                1
            )
        
        return frame
    
    def render_all(self, frame, fps: float, stats: dict, frame_times: List[float]) -> np.ndarray:
        """
        Render all FPS overlays.
        
        Args:
            frame: Input frame
            fps: Current FPS value
            stats: Statistics dictionary
            frame_times: List of recent frame times
            
        Returns:
            Frame with all overlays
        """
        frame = self.render_main_fps(frame, fps)
        frame = self.render_detailed_stats(frame, stats)
        frame = self.render_fps_graph(frame, frame_times)
        return frame
