"""
Demo: Complete detection pipeline with preprocessing and YOLO.

Shows how to:
1. Use detect_objects() function for simple detection
2. Get results in different formats (dict, tuple, detections)
3. Filter detections by confidence and class
4. Group detections by class
5. Process video streams with detection

Run: python demo_detection_pipeline.py
"""

import cv2
import numpy as np
import time
from src.video_streaming import Camera
from src.preprocessing import ImageProcessor
from src.yolo_inference import (
    YOLODetector,
    detect_objects,
    detect_and_filter,
    get_detections_by_class,
    stream_detect,
    get_detection_summary
)


def demo_basic_detection():
    """Demo 1: Basic detection with different return formats."""
    print("=" * 70)
    print("Demo 1: Basic Detection Function")
    print("=" * 70)
    
    # Initialize
    detector = YOLODetector("yolov8n.pt", device="auto")
    detector.load_model()
    
    camera = Camera(source=0, fps=30)
    
    print("\n🎥 Capturing frame...")
    for frame in camera.stream():
        
        # Method 1: Dictionary format (recommended)
        print("\n1️⃣ Dictionary format:")
        results = detect_objects(frame, detector, return_format="dict")
        print(f"   Detections: {results['num_detections']}")
        print(f"   Classes: {results['classes']}")
        print(f"   Confidences: {[f'{c:.2f}' for c in results['confidences']]}")
        print(f"   Boxes: {results['boxes'][:2]}...")  # Show first 2
        
        # Method 2: Tuple format
        print("\n2️⃣ Tuple format:")
        boxes, classes, confidences = detect_objects(
            frame, detector, return_format="tuple"
        )
        print(f"   Boxes: {len(boxes)}")
        print(f"   Classes: {classes}")
        print(f"   Confidences: {confidences}")
        
        # Method 3: Detection objects
        print("\n3️⃣ Detection objects format:")
        detections = detect_objects(frame, detector, return_format="detections")
        print(f"   Detections: {len(detections)}")
        for i, det in enumerate(detections[:3], 1):  # Show first 3
            print(f"   {i}. {det.class_name}: {det.confidence:.3f}")
        
        # Print summary
        print("\n📊 Summary:")
        print(get_detection_summary(results))
        
        break
    
    camera.release()


def demo_filtered_detection():
    """Demo 2: Detection with filtering options."""
    print("\n" + "=" * 70)
    print("Demo 2: Filtered Detection")
    print("=" * 70)
    
    detector = YOLODetector("yolov8n.pt", device="auto")
    detector.load_model()
    
    camera = Camera(source=0, fps=30)
    
    print("\n🎥 Detecting with filters...")
    
    for frame in camera.stream():
        # Detect only persons and cars with high confidence
        results = detect_and_filter(
            frame,
            detector,
            min_confidence=0.7,
            allowed_classes=['person', 'car', 'dog', 'cat'],
            max_detections=5
        )
        
        print(f"\n✅ Filtered Results:")
        print(f"   Total detections: {results['num_detections']}")
        
        if results['num_detections'] > 0:
            for cls, conf, bbox in zip(results['classes'], 
                                       results['confidences'],
                                       results['boxes']):
                print(f"   - {cls}: {conf:.3f} at {bbox}")
        
        # Show for 3 frames
        time.sleep(1)
        break
    
    camera.release()


def demo_grouped_detection():
    """Demo 3: Group detections by class."""
    print("\n" + "=" * 70)
    print("Demo 3: Grouped Detection by Class")
    print("=" * 70)
    
    detector = YOLODetector("yolov8n.pt", device="auto")
    detector.load_model()
    
    camera = Camera(source=0, fps=30)
    
    print("\n🎥 Detecting and grouping by class...")
    
    for frame in camera.stream():
        # Get detections grouped by class
        grouped = get_detections_by_class(frame, detector, group_by_class=True)
        
        print(f"\n📦 Grouped Results:")
        print(f"   Classes detected: {len(grouped)}")
        
        for class_name, detections in grouped.items():
            print(f"\n   {class_name.upper()}: {len(detections)} instances")
            for i, det in enumerate(detections, 1):
                print(f"      {i}. confidence={det['confidence']:.3f}")
        
        break
    
    camera.release()


def demo_realtime_with_preprocessing():
    """Demo 4: Complete pipeline with preprocessing."""
    print("\n" + "=" * 70)
    print("Demo 4: Complete Detection Pipeline")
    print("Press 'q' to quit")
    print("=" * 70)
    
    # Initialize detector
    detector = YOLODetector("yolov8n.pt", device="auto", confidence_threshold=0.5)
    detector.load_model()
    detector.warmup()
    
    # Initialize preprocessor
    preprocessor = ImageProcessor(
        target_size=(640, 640),
        normalize=False,  # YOLO handles normalization
        bgr_to_rgb=False,  # Keep BGR for YOLO
        keep_aspect_ratio=True
    )
    
    # Initialize camera
    camera = Camera(source=0, fps=30)
    
    print("\n🎥 Starting real-time detection pipeline...")
    
    frame_count = 0
    total_time = 0
    
    try:
        for frame in camera.stream():
            start_time = time.time()
            
            # Step 1: Preprocess
            original, processed = preprocessor.process(frame, return_original=True)
            
            # Step 2: Detect
            results = detect_objects(processed, detector, return_format="dict")
            
            # Step 3: Draw results on original frame
            for bbox, cls, conf in zip(results['boxes'], 
                                       results['classes'],
                                       results['confidences']):
                x1, y1, x2, y2 = map(int, bbox)
                
                # Draw box
                cv2.rectangle(original, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw label
                label = f"{cls} {conf:.2f}"
                cv2.putText(original, label, (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Calculate FPS
            frame_time = time.time() - start_time
            total_time += frame_time
            frame_count += 1
            avg_fps = frame_count / total_time if total_time > 0 else 0
            
            # Draw info
            info = [
                f"FPS: {avg_fps:.1f}",
                f"Frame time: {frame_time*1000:.1f}ms",
                f"Objects: {results['num_detections']}"
            ]
            
            y_pos = 30
            for text in info:
                cv2.putText(original, text, (10, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                y_pos += 30
            
            cv2.imshow('Detection Pipeline', original)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        camera.release()
        cv2.destroyAllWindows()
        
        print(f"\n📊 Statistics:")
        print(f"   Frames processed: {frame_count}")
        print(f"   Average FPS: {frame_count / total_time:.2f}")


def demo_stream_detection():
    """Demo 5: Using stream_detect generator."""
    print("\n" + "=" * 70)
    print("Demo 5: Stream Detection Generator")
    print("Processing 30 frames...")
    print("=" * 70)
    
    detector = YOLODetector("yolov8n.pt", device="auto")
    detector.load_model()
    
    camera = Camera(source=0, fps=30)
    
    # Callback function
    def on_detection(frame, results):
        if results['num_detections'] > 0:
            print(f"   Frame: {results['num_detections']} objects - "
                  f"Classes: {set(results['classes'])}")
    
    print("\n🎥 Processing stream...")
    
    # Use stream_detect generator
    for frame, results in stream_detect(
        camera.stream(),
        detector,
        callback=on_detection,
        max_frames=30
    ):
        # You can process frame and results here
        pass
    
    camera.release()
    print("\n✅ Stream processing complete")


def demo_single_frame_function():
    """Demo 6: Simple single function for detection."""
    print("\n" + "=" * 70)
    print("Demo 6: Simple Single Function Usage")
    print("=" * 70)
    
    print("\n💡 Complete example in a single function:\n")
    
    code = '''
def detect_frame(frame, detector):
    """
    Simple function that takes a frame and returns detections.
    
    Args:
        frame: Input frame (preprocessed or raw)
        detector: YOLODetector instance
        
    Returns:
        Dictionary with boxes, classes, and confidences
    """
    from src.yolo_inference import detect_objects
    
    # Run detection
    results = detect_objects(frame, detector, return_format="dict")
    
    # Returns:
    # {
    #     'boxes': [[x1, y1, x2, y2], ...],
    #     'classes': ['person', 'car', ...],
    #     'confidences': [0.95, 0.87, ...],
    #     'num_detections': 2
    # }
    
    return results


# Usage:
from src.yolo_inference import YOLODetector

detector = YOLODetector("yolov8n.pt", device="auto")
detector.load_model()

# Detect on a frame
results = detect_frame(frame, detector)

# Access results
for bbox, cls, conf in zip(results['boxes'], 
                           results['classes'], 
                           results['confidences']):
    print(f"{cls}: {conf:.2f} at {bbox}")
'''
    
    print(code)
    
    # Actually run it
    print("\n🎥 Running the example...")
    
    detector = YOLODetector("yolov8n.pt", device="auto")
    detector.load_model()
    
    camera = Camera(source=0, fps=30)
    
    for frame in camera.stream():
        results = detect_objects(frame, detector, return_format="dict")
        
        print(f"\n✅ Results:")
        print(f"   Detections: {results['num_detections']}")
        if results['num_detections'] > 0:
            for bbox, cls, conf in zip(results['boxes'][:3], 
                                       results['classes'][:3], 
                                       results['confidences'][:3]):
                print(f"   - {cls}: {conf:.2f}")
        
        break
    
    camera.release()


def main():
    """Run detection pipeline demos."""
    print("\n" + "=" * 70)
    print(" " * 15 + "DETECTION PIPELINE DEMO")
    print("=" * 70)
    
    demos = [
        ("Basic Detection Function", demo_basic_detection),
        ("Filtered Detection", demo_filtered_detection),
        ("Grouped by Class", demo_grouped_detection),
        ("Real-time Pipeline", demo_realtime_with_preprocessing),
        ("Stream Detection", demo_stream_detection),
        ("Simple Function Usage", demo_single_frame_function),
    ]
    
    print("\nAvailable demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  0. Run all demos")
    
    try:
        choice = input("\nSelect demo (0-6): ").strip()
        
        if choice == "0":
            for name, demo_func in demos:
                try:
                    demo_func()
                except Exception as e:
                    print(f"Error in {name}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        elif choice.isdigit() and 1 <= int(choice) <= len(demos):
            demos[int(choice) - 1][1]()
        else:
            print("Invalid choice")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Demo completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
