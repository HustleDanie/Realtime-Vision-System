"""
Demo: Drawing bounding boxes with OpenCV visualization utilities.

Shows how to:
1. Draw bounding boxes with labels and confidence scores
2. Customize box colors and styling
3. Add detection information overlays
4. Create color palettes for classes
5. Real-time visualization with YOLO

Run: python demo_visualization.py
"""

import cv2
import numpy as np
import time
from src.video_streaming import Camera
from src.preprocessing import ImageProcessor
from src.yolo_inference import YOLODetector, detect_objects
from src.utils.visualization import (
    draw_bounding_boxes,
    draw_detection_info,
    create_color_palette,
    Visualizer
)


def demo_basic_drawing():
    """Demo 1: Basic bounding box drawing."""
    print("=" * 70)
    print("Demo 1: Basic Bounding Box Drawing")
    print("=" * 70)
    
    # Create a test image
    image = np.ones((480, 640, 3), dtype=np.uint8) * 255
    
    # Example detection results
    boxes = [
        [50, 50, 200, 200],
        [250, 100, 450, 300],
        [100, 300, 300, 450]
    ]
    labels = ['person', 'car', 'dog']
    confidences = [0.95, 0.87, 0.76]
    
    print("\n📦 Drawing boxes:")
    print(f"   Boxes: {len(boxes)}")
    print(f"   Labels: {labels}")
    print(f"   Confidences: {confidences}")
    
    # Draw bounding boxes
    result = draw_bounding_boxes(
        image,
        boxes,
        labels,
        confidences,
        thickness=2,
        font_scale=0.6
    )
    
    # Display
    cv2.imshow('Basic Drawing', result)
    print("\n✅ Press any key to continue...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def demo_custom_colors():
    """Demo 2: Custom colors for different classes."""
    print("\n" + "=" * 70)
    print("Demo 2: Custom Colors")
    print("=" * 70)
    
    # Create test image
    image = np.ones((480, 640, 3), dtype=np.uint8) * 255
    
    # Detection results
    boxes = [
        [50, 50, 200, 200],
        [250, 100, 450, 300],
        [100, 300, 300, 450]
    ]
    labels = ['person', 'car', 'dog']
    confidences = [0.95, 0.87, 0.76]
    
    # Define custom colors (BGR format)
    colors = [
        (0, 255, 0),    # Green for person
        (255, 0, 0),    # Blue for car
        (0, 0, 255)     # Red for dog
    ]
    
    print("\n🎨 Using custom colors:")
    for label, color in zip(labels, colors):
        print(f"   {label}: BGR{color}")
    
    # Draw with custom colors
    result = draw_bounding_boxes(
        image,
        boxes,
        labels,
        confidences,
        colors=colors,
        thickness=3,
        font_scale=0.7
    )
    
    cv2.imshow('Custom Colors', result)
    print("\n✅ Press any key to continue...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def demo_color_palette():
    """Demo 3: Generate color palette for many classes."""
    print("\n" + "=" * 70)
    print("Demo 3: Color Palette Generation")
    print("=" * 70)
    
    # Create test image
    image = np.ones((600, 800, 3), dtype=np.uint8) * 255
    
    # Generate 10 classes with distinct colors
    num_classes = 10
    colors = create_color_palette(num_classes, colormap="hsv")
    
    print(f"\n🎨 Generated {num_classes} distinct colors:")
    
    # Create sample boxes
    boxes = []
    labels = []
    confidences = []
    
    for i in range(num_classes):
        x = 50 + (i % 5) * 150
        y = 50 + (i // 5) * 250
        boxes.append([x, y, x + 120, y + 200])
        labels.append(f"class_{i}")
        confidences.append(0.85 + i * 0.01)
    
    # Draw with generated colors
    result = draw_bounding_boxes(
        image,
        boxes,
        labels,
        confidences,
        colors=colors,
        thickness=2
    )
    
    cv2.imshow('Color Palette', result)
    print("\n✅ Press any key to continue...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def demo_with_info_overlay():
    """Demo 4: Add information overlay."""
    print("\n" + "=" * 70)
    print("Demo 4: Information Overlay")
    print("=" * 70)
    
    # Create test image
    image = np.ones((480, 640, 3), dtype=np.uint8) * 255
    
    # Draw some boxes
    boxes = [[100, 100, 300, 300], [350, 150, 550, 350]]
    labels = ['person', 'car']
    confidences = [0.95, 0.87]
    
    result = draw_bounding_boxes(image, boxes, labels, confidences)
    
    # Add information overlay
    info = [
        'FPS: 30.5',
        'Objects: 2',
        'Device: GPU',
        'Model: YOLOv8n'
    ]
    
    result = draw_detection_info(
        result,
        info,
        position=(10, 30),
        font_scale=0.7,
        color=(0, 255, 0),
        background=True
    )
    
    print("\n📊 Added info overlay:")
    for line in info:
        print(f"   {line}")
    
    cv2.imshow('With Info Overlay', result)
    print("\n✅ Press any key to continue...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def demo_realtime_visualization():
    """Demo 5: Real-time visualization with YOLO detection."""
    print("\n" + "=" * 70)
    print("Demo 5: Real-time Visualization")
    print("Press 'q' to quit")
    print("=" * 70)
    
    try:
        # Initialize detector
        detector = YOLODetector("yolov8n.pt", device="auto", confidence_threshold=0.5)
        detector.load_model()
        detector.warmup()
        
        # Generate colors for COCO classes (80 classes)
        colors = create_color_palette(80, colormap="hsv")
        
        # Map class names to colors
        class_color_map = {}
        if hasattr(detector.model, 'names'):
            for class_id, class_name in detector.model.names.items():
                class_color_map[class_name] = colors[class_id % len(colors)]
        
        # Initialize camera
        camera = Camera(source=0, fps=30)
        
        print("\n🎥 Starting real-time detection with visualization...")
        
        frame_times = []
        
        for frame in camera.stream():
            start_time = time.time()
            
            # Detect objects
            results = detect_objects(frame, detector, return_format="dict")
            
            # Get colors for detected classes
            box_colors = []
            for cls in results['classes']:
                box_colors.append(class_color_map.get(cls, (0, 255, 0)))
            
            # Draw bounding boxes
            visualized = draw_bounding_boxes(
                frame,
                results['boxes'],
                results['classes'],
                results['confidences'],
                colors=box_colors,
                thickness=2,
                font_scale=0.6
            )
            
            # Calculate FPS
            frame_time = time.time() - start_time
            frame_times.append(frame_time)
            if len(frame_times) > 30:
                frame_times.pop(0)
            
            avg_fps = 1.0 / np.mean(frame_times) if frame_times else 0
            
            # Add info overlay
            info = [
                f"FPS: {avg_fps:.1f}",
                f"Inference: {frame_time*1000:.1f}ms",
                f"Objects: {results['num_detections']}",
                f"Device: {detector.device.type.upper()}"
            ]
            
            visualized = draw_detection_info(
                visualized,
                info,
                position=(10, 30),
                color=(0, 255, 0)
            )
            
            # Display
            cv2.imshow('Real-time Detection', visualized)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        camera.release()
        cv2.destroyAllWindows()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   Note: This demo requires a YOLO model and webcam")


def demo_visualizer_class():
    """Demo 6: Using the Visualizer class."""
    print("\n" + "=" * 70)
    print("Demo 6: Visualizer Class")
    print("=" * 70)
    
    # Create visualizer with custom settings
    class_colors = {
        0: (0, 255, 0),   # Green for class 0
        1: (255, 0, 0),   # Blue for class 1
        2: (0, 0, 255),   # Red for class 2
    }
    
    visualizer = Visualizer(
        class_colors=class_colors,
        default_color=(255, 255, 0)
    )
    
    # Create test image
    image = np.ones((480, 640, 3), dtype=np.uint8) * 255
    
    # Simulated detection results dictionary
    results = {
        'boxes': [[50, 50, 200, 200], [250, 100, 450, 300]],
        'classes': ['person', 'car'],
        'confidences': [0.95, 0.87]
    }
    
    print("\n🎨 Using Visualizer class:")
    print(f"   Class colors: {class_colors}")
    
    # Draw using visualizer
    result = visualizer.draw_from_results(image, results)
    
    cv2.imshow('Visualizer Class', result)
    print("\n✅ Press any key to continue...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def demo_styling_options():
    """Demo 7: Different styling options."""
    print("\n" + "=" * 70)
    print("Demo 7: Styling Options")
    print("=" * 70)
    
    # Create test images
    boxes = [[100, 100, 300, 300]]
    labels = ['person']
    confidences = [0.95]
    colors = [(0, 255, 0)]
    
    styles = [
        {"thickness": 1, "font_scale": 0.4, "title": "Thin lines, small font"},
        {"thickness": 3, "font_scale": 0.7, "title": "Thick lines, large font"},
        {"thickness": 2, "font_scale": 0.5, "alpha": 0.5, "title": "Semi-transparent labels"},
        {"thickness": 2, "font_scale": 0.5, "show_confidence": False, "title": "No confidence scores"}
    ]
    
    images = []
    
    for style in styles:
        title = style.pop("title")
        image = np.ones((300, 400, 3), dtype=np.uint8) * 255
        
        result = draw_bounding_boxes(
            image,
            boxes,
            labels,
            confidences,
            colors=colors,
            **style
        )
        
        # Add title
        cv2.putText(result, title, (10, 280),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        images.append(result)
    
    # Create grid
    from src.utils.visualization import Visualizer
    visualizer = Visualizer()
    grid = visualizer.create_grid(images, grid_size=(2, 2))
    
    print("\n🎨 Showing different styling options:")
    for i, style in enumerate(styles, 1):
        print(f"   {i}. Various thickness and font settings")
    
    cv2.imshow('Styling Options', grid)
    print("\n✅ Press any key to continue...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def show_usage_example():
    """Show simple usage example."""
    print("\n" + "=" * 70)
    print("Simple Usage Example")
    print("=" * 70)
    
    code = '''
# Basic usage example:
from src.utils.visualization import draw_bounding_boxes
import cv2

# Your detection results
boxes = [[100, 50, 300, 250], [400, 100, 600, 350]]
labels = ['person', 'car']
confidences = [0.95, 0.87]

# Draw bounding boxes
result = draw_bounding_boxes(
    image,
    boxes,
    labels,
    confidences,
    thickness=2,
    font_scale=0.6
)

# Display
cv2.imshow('Detections', result)
cv2.waitKey(0)

# With custom colors:
colors = [(0, 255, 0), (255, 0, 0)]  # Green, Blue
result = draw_bounding_boxes(
    image, boxes, labels, confidences,
    colors=colors
)

# With information overlay:
from src.utils.visualization import draw_detection_info

info = ['FPS: 30', 'Objects: 2', 'Device: GPU']
result = draw_detection_info(result, info)
'''
    
    print(code)


def main():
    """Run visualization demos."""
    print("\n" + "=" * 70)
    print(" " * 15 + "VISUALIZATION DEMO")
    print(" " * 10 + "OpenCV Bounding Box Drawing")
    print("=" * 70)
    
    demos = [
        ("Basic Drawing", demo_basic_drawing),
        ("Custom Colors", demo_custom_colors),
        ("Color Palette", demo_color_palette),
        ("Info Overlay", demo_with_info_overlay),
        ("Real-time Detection", demo_realtime_visualization),
        ("Visualizer Class", demo_visualizer_class),
        ("Styling Options", demo_styling_options),
        ("Usage Example", show_usage_example),
    ]
    
    print("\nAvailable demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  0. Run all demos")
    
    try:
        choice = input("\nSelect demo (0-8): ").strip()
        
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
