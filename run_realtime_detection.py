"""
Real-time object detection pipeline - Main entry point.

This script runs the complete end-to-end detection pipeline:
1. Camera streaming (reads frames from webcam/video)
2. Image preprocessing (resize, normalize, BGR→RGB)
3. YOLO inference (object detection with GPU/CPU)
4. Visualization (draws bounding boxes with labels)
5. FPS monitoring (real-time performance metrics)

Usage:
    python run_realtime_detection.py               # Uses webcam
    python run_realtime_detection.py --model yolov8m.pt
    python run_realtime_detection.py --conf 0.4
    python run_realtime_detection.py --device cpu

Keyboard shortcuts (during execution):
    q - Quit
    p - Pause/Resume
    f - Toggle FPS counter
    g - Toggle FPS graph
    d - Toggle detailed statistics
    s - Save frame

FPS Display:
    - Large FPS number in top-left corner
    - Optional FPS graph showing performance over time (top-right)
    - Optional detailed statistics (min/max/average FPS)
    - Color coding: Green (good) → Orange (medium) → Red (low)
"""

import argparse
import logging
from pathlib import Path
import sys

from src.utils import DetectionPipeline


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_parser():
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Real-time object detection pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_realtime_detection.py
  python run_realtime_detection.py --model yolov8m.pt
  python run_realtime_detection.py --conf 0.4
  python run_realtime_detection.py --device cpu
        """
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n.pt",
        help="YOLO model path (default: yolov8n.pt)"
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.5,
        help="Confidence threshold (default: 0.5)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "gpu", "cpu"],
        help="Device to use (default: auto)"
    )
    parser.add_argument(
        "--model-version",
        type=str,
        default=None,
        help="Model version tag (default: derived from model filename)",
    )
    parser.add_argument(
        "--enable-logging",
        action="store_true",
        help="Enable logging predictions to DB/disk via VisionLogger",
    )
    parser.add_argument(
        "--log-all",
        action="store_true",
        help="Log non-defect frames as well (default: defects only)",
    )
    
    return parser


def print_banner(args):
    """Print startup banner."""
    print("\n" + "="*70)
    print("  REAL-TIME OBJECT DETECTION PIPELINE")
    print("="*70)
    print(f"\n📋 Configuration:")
    print(f"   Model: {args.model}")
    model_version = args.model_version or Path(args.model).stem
    print(f"   Model version: {model_version}")
    print(f"   Confidence: {args.conf}")
    print(f"   Device: {args.device}")
    print(f"   Logging: {'ON' if args.enable_logging else 'OFF'}")
    if args.enable_logging:
        print(f"   Log mode: {'all frames' if args.log_all else 'defects only'}")
    print(f"   Source: Webcam\n")


def main():
    """Main entry point."""
    # Setup
    setup_logging()
    parser = create_parser()
    args = parser.parse_args()
    
    # Print banner
    print_banner(args)
    
    try:
        # Create and run pipeline
        pipeline = DetectionPipeline(
            model_path=args.model,
            confidence_threshold=args.conf,
            device=args.device,
            model_version=args.model_version,
            enable_logging=args.enable_logging,
            log_defects_only=not args.log_all,
        )
        
        pipeline.run()
        
        print("\n" + "="*70)
        print("Detection completed successfully!")
        print("="*70 + "\n")
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
