"""
Simple standalone example: Load YOLO model with GPU/CPU auto-detection.

This shows the essential code for loading YOLO models with PyTorch
and automatically selecting GPU if available, otherwise CPU.

Run: python example_yolo_simple.py
"""

import torch
import cv2
import numpy as np
from pathlib import Path


def setup_device(device="auto"):
    """
    Setup compute device with automatic GPU/CPU selection.
    
    Args:
        device: 'auto', 'cuda', 'cpu', or specific device like 'cuda:0'
        
    Returns:
        torch.device object
    """
    if device == "auto":
        if torch.cuda.is_available():
            device = torch.device("cuda")
            print(f"✅ GPU Available: {torch.cuda.get_device_name(0)}")
            print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        else:
            device = torch.device("cpu")
            print("⚠️  No GPU available, using CPU")
    else:
        device = torch.device(device)
        print(f"Using specified device: {device}")
    
    return device


def load_yolov8_model(model_path="yolov8n.pt", device="auto"):
    """
    Load YOLOv8 model with automatic device selection.
    
    Args:
        model_path: Path to YOLO model (.pt file)
        device: Compute device ('auto', 'cuda', 'cpu')
        
    Returns:
        Loaded YOLO model
    """
    print(f"\n📦 Loading YOLOv8 model: {model_path}")
    
    # Setup device
    device_obj = setup_device(device)
    
    # Import ultralytics
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError("Install ultralytics: pip install ultralytics")
    
    # Load model
    model = YOLO(model_path)
    
    # Move to device
    model.to(device_obj)
    
    print(f"✅ Model loaded on {device_obj}")
    
    return model, device_obj


def load_yolov5_model(model_name="yolov5n", device="auto"):
    """
    Load YOLOv5 model from torch.hub with device selection.
    
    Args:
        model_name: YOLOv5 model name ('yolov5n', 'yolov5s', etc.)
        device: Compute device ('auto', 'cuda', 'cpu')
        
    Returns:
        Loaded YOLO model
    """
    print(f"\n📦 Loading YOLOv5 model: {model_name}")
    
    # Setup device
    device_obj = setup_device(device)
    
    # Load model from torch hub
    model = torch.hub.load('ultralytics/yolov5', model_name, pretrained=True)
    
    # Move to device
    model.to(device_obj)
    model.eval()
    
    print(f"✅ Model loaded on {device_obj}")
    
    return model, device_obj


def warmup_model(model, device, input_size=(640, 640), iterations=3):
    """
    Warm up model for faster inference.
    
    Args:
        model: YOLO model
        device: torch.device
        input_size: Input image size (width, height)
        iterations: Number of warmup iterations
    """
    print(f"\n🔥 Warming up model ({iterations} iterations)...")
    
    # Create dummy input
    dummy_input = np.zeros((input_size[1], input_size[0], 3), dtype=np.uint8)
    
    # Run warmup
    for i in range(iterations):
        _ = model(dummy_input, verbose=False)
    
    print("✅ Warmup complete")


def run_inference_yolov8(model, image, conf_threshold=0.5):
    """
    Run YOLOv8 inference on an image.
    
    Args:
        model: YOLOv8 model
        image: Input image (numpy array)
        conf_threshold: Confidence threshold
        
    Returns:
        List of detections
    """
    # Run inference
    results = model(image, conf=conf_threshold, verbose=False)
    
    # Parse results
    detections = []
    for result in results:
        boxes = result.boxes
        for i in range(len(boxes)):
            detection = {
                'bbox': boxes.xyxy[i].cpu().numpy().tolist(),
                'confidence': float(boxes.conf[i].cpu().numpy()),
                'class_id': int(boxes.cls[i].cpu().numpy()),
                'class_name': model.names[int(boxes.cls[i].cpu().numpy())]
            }
            detections.append(detection)
    
    return detections


def run_inference_yolov5(model, image, conf_threshold=0.5):
    """
    Run YOLOv5 inference on an image.
    
    Args:
        model: YOLOv5 model
        image: Input image (numpy array)
        conf_threshold: Confidence threshold
        
    Returns:
        List of detections
    """
    # Set confidence threshold
    model.conf = conf_threshold
    
    # Run inference
    results = model(image)
    
    # Parse results
    detections = []
    for *bbox, conf, cls in results.xyxy[0].cpu().numpy():
        detection = {
            'bbox': bbox,
            'confidence': float(conf),
            'class_id': int(cls),
            'class_name': model.names[int(cls)]
        }
        detections.append(detection)
    
    return detections


def example_webcam_yolov8():
    """Example: Real-time webcam inference with YOLOv8."""
    print("\n" + "=" * 70)
    print("Example: Real-time Webcam Detection (YOLOv8)")
    print("Press 'q' to quit")
    print("=" * 70)
    
    # Load model
    model, device = load_yolov8_model("yolov8n.pt", device="auto")
    
    # Warm up
    warmup_model(model, device)
    
    # Open webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Failed to open webcam")
        return
    
    print("\n🎥 Starting detection...")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Run inference
            detections = run_inference_yolov8(model, frame, conf_threshold=0.5)
            
            # Draw detections
            for det in detections:
                x1, y1, x2, y2 = map(int, det['bbox'])
                
                # Draw box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw label
                label = f"{det['class_name']} {det['confidence']:.2f}"
                cv2.putText(frame, label, (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Show device info
            cv2.putText(frame, f"Device: {device.type.upper()}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Objects: {len(detections)}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Display
            cv2.imshow('YOLOv8 Detection', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\n✅ Detection stopped")


def example_image_inference():
    """Example: Single image inference."""
    print("\n" + "=" * 70)
    print("Example: Single Image Inference")
    print("=" * 70)
    
    # Load model
    model, device = load_yolov8_model("yolov8n.pt", device="auto")
    
    # Create test image (or load from file)
    image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    print(f"\n📷 Image shape: {image.shape}")
    
    # Run inference
    import time
    start = time.time()
    detections = run_inference_yolov8(model, image, conf_threshold=0.5)
    elapsed = time.time() - start
    
    print(f"✅ Inference complete")
    print(f"   Time: {elapsed*1000:.2f}ms")
    print(f"   Detections: {len(detections)}")
    
    # Print detections
    for i, det in enumerate(detections, 1):
        print(f"   {i}. {det['class_name']}: {det['confidence']:.3f}")


def show_device_capabilities():
    """Show PyTorch device capabilities."""
    print("\n" + "=" * 70)
    print("PyTorch Device Capabilities")
    print("=" * 70)
    
    print(f"\n📊 PyTorch Version: {torch.__version__}")
    print(f"   CUDA Available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"   CUDA Version: {torch.version.cuda}")
        print(f"   cuDNN Version: {torch.backends.cudnn.version()}")
        print(f"   Number of GPUs: {torch.cuda.device_count()}")
        
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            print(f"\n   GPU {i}: {torch.cuda.get_device_name(i)}")
            print(f"      Memory: {props.total_memory / 1e9:.2f} GB")
            print(f"      Compute Capability: {props.major}.{props.minor}")
    
    # Check MPS (Apple Silicon)
    if hasattr(torch.backends, 'mps'):
        print(f"   MPS (Apple) Available: {torch.backends.mps.is_available()}")


def main():
    """Main entry point."""
    print("\n" + "=" * 70)
    print(" " * 15 + "YOLO PyTorch GPU/CPU Example")
    print("=" * 70)
    
    examples = [
        ("Show Device Info", show_device_capabilities),
        ("Single Image Inference", example_image_inference),
        ("Webcam Detection (YOLOv8)", example_webcam_yolov8),
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    try:
        choice = input("\nSelect example (1-3): ").strip()
        
        if choice.isdigit() and 1 <= int(choice) <= len(examples):
            examples[int(choice) - 1][1]()
        else:
            print("Invalid choice")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
