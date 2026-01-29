"""
Demo script for real-time preprocessing with camera streams.

Shows how to:
1. Process frames in real-time
2. Return both original and processed frames
3. Apply different normalization types
4. Use custom transforms
5. Process video streams

Run: python demo_preprocessing.py
"""

import cv2
import numpy as np
import time
from src.video_streaming import Camera
from src.preprocessing import (
    ImageProcessor,
    ResizeTransform,
    NormalizeTransform,
    BGRToRGBTransform,
    GaussianBlurTransform
)


def demo_basic_preprocessing():
    """Demo 1: Basic preprocessing with original and processed frames."""
    print("=" * 70)
    print("Demo 1: Basic Preprocessing")
    print("Press 'q' to quit")
    print("=" * 70)
    
    # Initialize preprocessor
    processor = ImageProcessor(
        target_size=(640, 640),
        normalize=True,
        normalization_type="0-1",
        bgr_to_rgb=True,
        keep_aspect_ratio=False
    )
    
    print("\nProcessor Configuration:")
    print(processor.get_info())
    
    with Camera(source=0, fps=30) as camera:
        for frame in camera.stream():
            # Process frame and get both original and processed
            original, processed = processor.process(frame, return_original=True)
            
            # Convert processed back to uint8 for display (if normalized)
            if processed.dtype == np.float32:
                display_processed = (processed * 255).astype(np.uint8)
            else:
                display_processed = processed
            
            # Convert RGB back to BGR for OpenCV display
            if processor.bgr_to_rgb:
                display_processed = cv2.cvtColor(display_processed, cv2.COLOR_RGB2BGR)
            
            # Add labels
            cv2.putText(original, "Original", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(display_processed, "Processed", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Resize original to match processed size for side-by-side display
            original_resized = cv2.resize(original, (640, 640))
            
            # Display side by side
            combined = np.hstack([original_resized, display_processed])
            cv2.imshow('Original vs Processed', combined)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cv2.destroyAllWindows()


def demo_normalization_types():
    """Demo 2: Different normalization types comparison."""
    print("\n" + "=" * 70)
    print("Demo 2: Normalization Types Comparison")
    print("Press 'q' to quit")
    print("=" * 70)
    
    # Create processors with different normalization types
    processors = {
        "0-1": ImageProcessor(
            target_size=(320, 320),
            normalize=True,
            normalization_type="0-1",
            bgr_to_rgb=False
        ),
        "ImageNet": ImageProcessor(
            target_size=(320, 320),
            normalize=True,
            normalization_type="imagenet",
            bgr_to_rgb=False
        ),
        "[-1,1]": ImageProcessor(
            target_size=(320, 320),
            normalize=True,
            normalization_type="minus1-1",
            bgr_to_rgb=False
        )
    }
    
    with Camera(source=0, fps=30) as camera:
        for frame in camera.stream():
            displays = []
            
            for name, proc in processors.items():
                processed = proc.process(frame, return_original=False)
                
                # Convert to displayable format
                if processed.dtype == np.float32:
                    # Rescale to [0, 255] for display
                    min_val, max_val = processed.min(), processed.max()
                    display = ((processed - min_val) / (max_val - min_val) * 255).astype(np.uint8)
                else:
                    display = processed
                
                # Add label
                cv2.putText(display, name, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                displays.append(display)
            
            # Stack horizontally
            combined = np.hstack(displays)
            cv2.imshow('Normalization Comparison', combined)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cv2.destroyAllWindows()


def demo_stream_processing():
    """Demo 3: Process camera stream with generator."""
    print("\n" + "=" * 70)
    print("Demo 3: Stream Processing with Generator")
    print("Processing 100 frames...")
    print("=" * 70)
    
    processor = ImageProcessor(
        target_size=(640, 640),
        normalize=True,
        normalization_type="imagenet",
        bgr_to_rgb=True
    )
    
    camera = Camera(source=0, fps=30)
    
    try:
        frame_count = 0
        start_time = time.time()
        
        # Process stream using generator
        for original, processed in processor.process_stream(camera.stream(), return_originals=True):
            frame_count += 1
            
            # Display info
            if frame_count % 10 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                print(f"Frame {frame_count} | FPS: {fps:.2f} | "
                      f"Processed shape: {processed.shape} | "
                      f"Processed dtype: {processed.dtype}")
            
            if frame_count >= 100:
                break
        
        total_time = time.time() - start_time
        print(f"\nProcessed {frame_count} frames in {total_time:.2f}s")
        print(f"Average FPS: {frame_count / total_time:.2f}")
        
    finally:
        camera.release()


def demo_custom_transforms():
    """Demo 4: Using custom transform pipeline."""
    print("\n" + "=" * 70)
    print("Demo 4: Custom Transform Pipeline")
    print("Press 'q' to quit")
    print("=" * 70)
    
    # Create processor without auto-processing
    processor = ImageProcessor(
        target_size=(640, 640),
        normalize=False,
        bgr_to_rgb=False
    )
    
    # Add custom transforms
    processor.add_transform(GaussianBlurTransform(kernel_size=(5, 5)))
    processor.add_transform(ResizeTransform((320, 320)))
    
    print("\nTransform Pipeline:")
    for i, transform in enumerate(processor.transforms, 1):
        print(f"  {i}. {transform.__class__.__name__}")
    
    with Camera(source=0, fps=30) as camera:
        for frame in camera.stream():
            # Process with custom pipeline
            original, processed = processor.process(frame, return_original=True)
            
            # Resize original to match for comparison
            original_small = cv2.resize(original, (320, 320))
            
            # Display side by side
            cv2.putText(original_small, "Original", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(processed, "Blurred + Resized", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            combined = np.hstack([original_small, processed])
            cv2.imshow('Custom Transforms', combined)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cv2.destroyAllWindows()


def demo_aspect_ratio_preservation():
    """Demo 5: Aspect ratio preservation with padding."""
    print("\n" + "=" * 70)
    print("Demo 5: Aspect Ratio Preservation")
    print("Press 'q' to quit")
    print("=" * 70)
    
    # Without aspect ratio preservation
    processor_stretch = ImageProcessor(
        target_size=(640, 480),
        normalize=False,
        bgr_to_rgb=False,
        keep_aspect_ratio=False
    )
    
    # With aspect ratio preservation
    processor_preserve = ImageProcessor(
        target_size=(640, 480),
        normalize=False,
        bgr_to_rgb=False,
        keep_aspect_ratio=True
    )
    
    with Camera(source=0, fps=30) as camera:
        for frame in camera.stream():
            # Process both ways
            stretched = processor_stretch.process(frame)
            preserved = processor_preserve.process(frame)
            
            # Add labels
            cv2.putText(stretched, "Stretched", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(preserved, "Aspect Ratio Preserved", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Stack vertically
            combined = np.vstack([stretched, preserved])
            cv2.imshow('Aspect Ratio Comparison', combined)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cv2.destroyAllWindows()


def demo_rgb_conversion():
    """Demo 6: BGR to RGB conversion visualization."""
    print("\n" + "=" * 70)
    print("Demo 6: BGR to RGB Conversion")
    print("Press 'q' to quit")
    print("=" * 70)
    
    processor_bgr = ImageProcessor(
        target_size=(640, 640),
        normalize=False,
        bgr_to_rgb=False
    )
    
    processor_rgb = ImageProcessor(
        target_size=(640, 640),
        normalize=False,
        bgr_to_rgb=True
    )
    
    with Camera(source=0, fps=30) as camera:
        for frame in camera.stream():
            # Process with and without BGR to RGB
            bgr_result = processor_bgr.process(frame)
            rgb_result = processor_rgb.process(frame)
            
            # Convert RGB back to BGR for display
            rgb_display = cv2.cvtColor(rgb_result, cv2.COLOR_RGB2BGR)
            
            # Add labels
            cv2.putText(bgr_result, "BGR (OpenCV)", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            cv2.putText(rgb_display, "RGB (ML Models)", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Display side by side
            combined = np.hstack([bgr_result, rgb_display])
            cv2.imshow('BGR vs RGB', combined)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cv2.destroyAllWindows()


def demo_batch_processing():
    """Demo 7: Batch processing multiple frames."""
    print("\n" + "=" * 70)
    print("Demo 7: Batch Processing")
    print("=" * 70)
    
    processor = ImageProcessor(
        target_size=(320, 320),
        normalize=True,
        normalization_type="0-1",
        bgr_to_rgb=True
    )
    
    camera = Camera(source=0, fps=30)
    
    try:
        # Collect a batch of frames
        batch_size = 10
        frames = []
        
        print(f"Collecting {batch_size} frames...")
        for i, frame in enumerate(camera.stream()):
            frames.append(frame)
            if i >= batch_size - 1:
                break
        
        # Process batch
        print("Processing batch...")
        start_time = time.time()
        originals, processed_batch = processor.batch_process(frames, return_originals=True)
        batch_time = time.time() - start_time
        
        print(f"\nBatch Statistics:")
        print(f"  Frames: {len(processed_batch)}")
        print(f"  Total time: {batch_time:.3f}s")
        print(f"  Time per frame: {batch_time / len(processed_batch):.3f}s")
        print(f"  Original shape: {originals[0].shape}")
        print(f"  Processed shape: {processed_batch[0].shape}")
        print(f"  Processed dtype: {processed_batch[0].dtype}")
        print(f"  Value range: [{processed_batch[0].min():.3f}, {processed_batch[0].max():.3f}]")
        
    finally:
        camera.release()


def main():
    """Run all preprocessing demos."""
    print("\n" + "=" * 70)
    print(" " * 20 + "PREPROCESSING DEMO")
    print("=" * 70)
    
    demos = [
        ("Basic Preprocessing", demo_basic_preprocessing),
        ("Normalization Types", demo_normalization_types),
        ("Stream Processing", demo_stream_processing),
        ("Custom Transforms", demo_custom_transforms),
        ("Aspect Ratio", demo_aspect_ratio_preservation),
        ("RGB Conversion", demo_rgb_conversion),
        ("Batch Processing", demo_batch_processing),
    ]
    
    print("\nAvailable demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  0. Run all demos")
    
    try:
        choice = input("\nSelect demo (0-7): ").strip()
        
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
