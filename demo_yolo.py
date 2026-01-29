"""
Demo script for YOLO real-time inference with GPU/CPU support.

Shows how to:
1. Load YOLO models with automatic device selection
2. Check GPU availability and device info
3. Run real-time inference on webcam
4. Warm up the model for optimal performance
5. Process video files
6. Benchmark inference speed

Requirements:
    pip install torch torchvision ultralytics opencv-python

Run: python demo_yolo.py
"""

import cv2
import time
import numpy as np
from pathlib import Path
from src.video_streaming import Camera
from src.preprocessing import ImageProcessor
from src.yolo_inference import YOLODetector, ModelLoader


def check_device_info():
    """Demo 1: Check available compute devices."""
    print("=" * 70)
    print("Demo 1: Device Information")
    print("=" * 70)
    
    loader = ModelLoader(device="auto")
    device_info = loader.get_device_info()
    
    print("\n📊 PyTorch & Device Information:")
    print(f"  PyTorch Version: {device_info['pytorch_version']}")
    print(f"  Device: {device_info['device']}")
    print(f"  Device Type: {device_info['device_type']}")
    print(f"  CUDA Available: {device_info['cuda_available']}")
    
    if device_info['cuda_available']:
        print(f"\n🎮 GPU Information:")
        print(f"  GPU Name: {device_info['gpu_name']}")
        print(f"  CUDA Version: {device_info['cuda_version']}")
        print(f"  cuDNN Version: {device_info['cudnn_version']}")
        print(f"  Number of GPUs: {device_info['num_gpus']}")
        print(f"  GPU Memory Total: {device_info['gpu_memory_total']}")
        print(f"  GPU Memory Allocated: {device_info['gpu_memory_allocated']}")
        print(f"  GPU Memory Reserved: {device_info['gpu_memory_reserved']}")
    
    if device_info.get('mps_available'):
        print(f"\n🍎 Apple MPS Available: Yes")


def demo_load_model():
    """Demo 2: Load YOLO model with automatic device selection."""
    print("\n" + "=" * 70)
    print("Demo 2: Loading YOLO Model")
    print("=" * 70)
    
    # Method 1: Direct detector initialization
    print("\n📦 Method 1: YOLODetector (recommended)")
    print("-" * 70)
    
    try:
        # This will download yolov8n.pt if not present
        detector = YOLODetector(
            model_path="yolov8n.pt",  # Nano model (fastest)
            confidence_threshold=0.5,
            nms_threshold=0.4,
            device="auto",  # Automatically select GPU or CPU
            model_type="yolov8",
            half_precision=False  # Set True for FP16 on GPU
        )
        
        print(f"  Detector: {detector}")
        
        # Load the model
        detector.load_model()
        
        # Get device info
        device_info = detector.get_device_info()
        print(f"\n  ✅ Model loaded successfully!")
        print(f"  Device: {device_info['device_type']}")
        print(f"  Half Precision: {device_info['half_precision']}")
        
        if device_info['device_type'] == 'cuda':
            print(f"  GPU: {device_info['gpu_name']}")
            print(f"  VRAM Allocated: {device_info['gpu_memory_allocated']}")
        
        # Warm up model
        print("\n  🔥 Warming up model...")
        detector.warmup(input_size=(640, 640), iterations=3)
        
        return detector
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print(f"  Note: Model will be downloaded automatically on first use")
        return None


def demo_model_loader():
    """Demo 3: Using ModelLoader for managing multiple models."""
    print("\n" + "=" * 70)
    print("Demo 3: ModelLoader for Multiple Models")
    print("=" * 70)
    
    loader = ModelLoader(
        models_dir="models",
        device="auto",
        cache_models=True
    )
    
    print(f"\n  Loader: {loader}")
    
    # List available models
    models = loader.list_models()
    print(f"\n  Available models in 'models' directory:")
    if models:
        for model in models:
            print(f"    - {model}")
    else:
        print(f"    (No models found)")
        print(f"    Download models from: https://github.com/ultralytics/yolov8/releases")
    
    # Show device info
    device_info = loader.get_device_info()
    print(f"\n  Device Configuration:")
    print(f"    Device: {device_info['device']}")
    print(f"    Type: {device_info['device_type']}")


def demo_realtime_detection(detector=None):
    """Demo 4: Real-time object detection on webcam."""
    print("\n" + "=" * 70)
    print("Demo 4: Real-time Detection on Webcam")
    print("Press 'q' to quit")
    print("=" * 70)
    
    if detector is None:
        print("\n  Loading detector...")
        try:
            detector = YOLODetector(
                model_path="yolov8n.pt",
                confidence_threshold=0.5,
                device="auto",
                model_type="yolov8"
            )
            detector.load_model()
            detector.warmup()
        except Exception as e:
            print(f"  ❌ Failed to load detector: {e}")
            return
    
    # Initialize camera
    camera = Camera(source=0, fps=30)
    
    # Performance tracking
    frame_times = []
    
    try:
        print("\n  🎥 Starting detection...")
        
        for frame in camera.stream():
            start_time = time.time()
            
            # Run detection
            detections = detector.detect(frame)
            
            # Calculate inference time
            inference_time = time.time() - start_time
            frame_times.append(inference_time)
            
            # Keep last 30 frame times
            if len(frame_times) > 30:
                frame_times.pop(0)
            
            # Calculate FPS
            avg_inference = np.mean(frame_times)
            fps = 1.0 / avg_inference if avg_inference > 0 else 0
            
            # Draw detections
            for det in detections:
                x1, y1, x2, y2 = map(int, det.bbox)
                
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw label
                label = f"{det.class_name} {det.confidence:.2f}"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(
                    frame,
                    (x1, y1 - label_size[1] - 10),
                    (x1 + label_size[0], y1),
                    (0, 255, 0),
                    -1
                )
                cv2.putText(
                    frame,
                    label,
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    2
                )
            
            # Draw performance info
            info_text = [
                f"FPS: {fps:.1f}",
                f"Inference: {avg_inference*1000:.1f}ms",
                f"Objects: {len(detections)}",
                f"Device: {detector.device.type.upper()}"
            ]
            
            y_offset = 30
            for text in info_text:
                cv2.putText(
                    frame,
                    text,
                    (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                y_offset += 30
            
            # Display frame
            cv2.imshow('YOLO Real-time Detection', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
    finally:
        camera.release()
        cv2.destroyAllWindows()
        
        # Print statistics
        if frame_times:
            print(f"\n  📊 Performance Statistics:")
            print(f"    Frames processed: {len(frame_times)}")
            print(f"    Average FPS: {1.0 / np.mean(frame_times):.2f}")
            print(f"    Average inference time: {np.mean(frame_times)*1000:.2f}ms")
            print(f"    Min inference time: {np.min(frame_times)*1000:.2f}ms")
            print(f"    Max inference time: {np.max(frame_times)*1000:.2f}ms")


def demo_benchmark():
    """Demo 5: Benchmark inference speed."""
    print("\n" + "=" * 70)
    print("Demo 5: Benchmark Inference Speed")
    print("=" * 70)
    
    try:
        detector = YOLODetector(
            model_path="yolov8n.pt",
            confidence_threshold=0.5,
            device="auto",
            model_type="yolov8"
        )
        detector.load_model()
        
        # Create test image
        test_sizes = [(320, 320), (640, 640), (1280, 1280)]
        num_iterations = 50
        
        print(f"\n  Running benchmark with {num_iterations} iterations...")
        print(f"  Device: {detector.device}")
        
        results = {}
        
        for size in test_sizes:
            print(f"\n  Testing size {size[0]}x{size[1]}...")
            
            # Create dummy image
            test_image = np.random.randint(0, 255, (size[1], size[0], 3), dtype=np.uint8)
            
            # Warmup
            for _ in range(5):
                _ = detector.detect(test_image)
            
            # Benchmark
            times = []
            for i in range(num_iterations):
                start = time.time()
                detections = detector.detect(test_image)
                elapsed = time.time() - start
                times.append(elapsed)
                
                if (i + 1) % 10 == 0:
                    print(f"    Iteration {i+1}/{num_iterations}")
            
            # Calculate statistics
            times = np.array(times)
            results[size] = {
                'mean': np.mean(times),
                'std': np.std(times),
                'min': np.min(times),
                'max': np.max(times),
                'fps': 1.0 / np.mean(times)
            }
        
        # Print results
        print(f"\n  📊 Benchmark Results:")
        print(f"  {'Size':<15} {'Mean (ms)':<12} {'Std (ms)':<12} {'FPS':<10}")
        print(f"  {'-'*50}")
        for size, stats in results.items():
            print(
                f"  {f'{size[0]}x{size[1]}':<15} "
                f"{stats['mean']*1000:<12.2f} "
                f"{stats['std']*1000:<12.2f} "
                f"{stats['fps']:<10.2f}"
            )
        
    except Exception as e:
        print(f"  ❌ Benchmark failed: {e}")


def demo_with_preprocessing():
    """Demo 6: YOLO with preprocessing pipeline."""
    print("\n" + "=" * 70)
    print("Demo 6: YOLO with Preprocessing")
    print("Press 'q' to quit")
    print("=" * 70)
    
    try:
        # Initialize detector
        detector = YOLODetector(
            model_path="yolov8n.pt",
            confidence_threshold=0.5,
            device="auto",
            model_type="yolov8"
        )
        detector.load_model()
        
        # Initialize preprocessor (YOLO typically expects BGR)
        preprocessor = ImageProcessor(
            target_size=(640, 640),
            normalize=False,  # YOLO handles normalization internally
            bgr_to_rgb=False,  # Keep BGR for YOLO
            keep_aspect_ratio=True
        )
        
        camera = Camera(source=0, fps=30)
        
        print("\n  🎥 Starting detection with preprocessing...")
        
        for frame in camera.stream():
            # Preprocess frame
            original, processed = preprocessor.process(frame, return_original=True)
            
            # Run detection
            detections = detector.detect(processed)
            
            # Draw on original frame
            for det in detections:
                x1, y1, x2, y2 = map(int, det.bbox)
                cv2.rectangle(original, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                label = f"{det.class_name} {det.confidence:.2f}"
                cv2.putText(
                    original,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2
                )
            
            cv2.imshow('Detection with Preprocessing', original)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        camera.release()
        cv2.destroyAllWindows()
        
    except Exception as e:
        print(f"  ❌ Error: {e}")


def main():
    """Run all YOLO demos."""
    print("\n" + "=" * 70)
    print(" " * 20 + "YOLO INFERENCE DEMO")
    print(" " * 15 + "GPU/CPU Automatic Selection")
    print("=" * 70)
    
    demos = [
        ("Device Information", check_device_info),
        ("Load YOLO Model", demo_load_model),
        ("ModelLoader Usage", demo_model_loader),
        ("Real-time Detection", lambda: demo_realtime_detection()),
        ("Benchmark Speed", demo_benchmark),
        ("With Preprocessing", demo_with_preprocessing),
    ]
    
    print("\nAvailable demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  0. Run all demos")
    
    try:
        choice = input("\nSelect demo (0-6): ").strip()
        
        if choice == "0":
            detector = None
            for name, demo_func in demos:
                try:
                    if name == "Load YOLO Model":
                        detector = demo_func()
                    elif name == "Real-time Detection":
                        demo_realtime_detection(detector)
                    else:
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
