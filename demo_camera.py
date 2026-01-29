"""
Demo script showing different ways to use the CameraStream class.

Run this script to test camera functionality:
    python demo_camera.py
"""

import cv2
import time
from src.video_streaming import Camera, CameraStream


def demo_basic_webcam():
    """Demo 1: Basic webcam streaming with FPS display."""
    print("=" * 60)
    print("Demo 1: Basic Webcam Streaming")
    print("Press 'q' to quit")
    print("=" * 60)
    
    with Camera(source=0, fps=30) as camera:
        for frame in camera.stream():
            # Get camera properties
            props = camera.get_properties()
            
            # Display info on frame
            cv2.putText(
                frame,
                f"FPS: {props['actual_fps']:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )
            
            cv2.putText(
                frame,
                f"Frame: {props['frame_count']}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )
            
            cv2.putText(
                frame,
                f"Resolution: {props['width']}x{props['height']}",
                (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )
            
            cv2.imshow('Camera Demo', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cv2.destroyAllWindows()


def demo_video_file():
    """Demo 2: Process video file frame by frame."""
    print("\n" + "=" * 60)
    print("Demo 2: Video File Processing")
    print("=" * 60)
    
    # Replace with your video file path
    video_path = "path/to/video.mp4"
    
    try:
        with CameraStream(source=video_path, fps=30) as camera:
            frame_count = 0
            start_time = time.time()
            
            for frame in camera.stream():
                frame_count += 1
                
                # Process frame here
                # Example: resize, apply filters, run detection, etc.
                
                if frame_count % 30 == 0:  # Print every 30 frames
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    print(f"Processed {frame_count} frames | Avg FPS: {fps:.2f}")
                
                # Optional: display frame
                # cv2.imshow('Video', frame)
                # if cv2.waitKey(1) & 0xFF == ord('q'):
                #     break
            
            total_time = time.time() - start_time
            print(f"\nCompleted: {frame_count} frames in {total_time:.2f}s")
            print(f"Average FPS: {frame_count / total_time:.2f}")
            
    except FileNotFoundError:
        print(f"Video file not found: {video_path}")
        print("Skipping this demo...")


def demo_threaded_mode():
    """Demo 3: Threaded mode for non-blocking frame reading."""
    print("\n" + "=" * 60)
    print("Demo 3: Threaded Camera Mode")
    print("Press 'q' to quit")
    print("=" * 60)
    
    camera = Camera(source=0, fps=30)
    camera.start_threaded()  # Start background thread
    
    try:
        while True:
            # Read latest frame (non-blocking)
            success, frame = camera.read()
            
            if success and frame is not None:
                props = camera.get_properties()
                
                cv2.putText(
                    frame,
                    f"Threaded Mode | FPS: {props['actual_fps']:.1f}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2
                )
                
                cv2.imshow('Threaded Camera', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            # Simulate other processing work
            time.sleep(0.01)
            
    finally:
        camera.release()
        cv2.destroyAllWindows()


def demo_custom_resolution():
    """Demo 4: Camera with custom resolution."""
    print("\n" + "=" * 60)
    print("Demo 4: Custom Resolution")
    print("Press 'q' to quit")
    print("=" * 60)
    
    with Camera(source=0, fps=30, resolution=(1280, 720)) as camera:
        props = camera.get_properties()
        print(f"Requested: 1280x720")
        print(f"Actual: {props['width']}x{props['height']}")
        
        for frame in camera.stream():
            cv2.putText(
                frame,
                f"Resolution: {frame.shape[1]}x{frame.shape[0]}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 0, 255),
                2
            )
            
            cv2.imshow('Custom Resolution', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    cv2.destroyAllWindows()


def demo_frame_generator():
    """Demo 5: Using camera as a generator for processing pipeline."""
    print("\n" + "=" * 60)
    print("Demo 5: Frame Generator Pipeline")
    print("=" * 60)
    
    camera = Camera(source=0, fps=30)
    
    # Process frames in a pipeline
    frame_count = 0
    start_time = time.time()
    
    try:
        for frame in camera.stream():
            frame_count += 1
            
            # Example processing pipeline
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            # Show processed frame
            cv2.imshow('Edge Detection', edges)
            
            if frame_count >= 100:  # Process 100 frames
                break
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        elapsed = time.time() - start_time
        print(f"Processed {frame_count} frames in {elapsed:.2f}s")
        print(f"Average FPS: {frame_count / elapsed:.2f}")
        
    finally:
        camera.release()
        cv2.destroyAllWindows()


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print(" " * 15 + "CAMERA STREAM DEMO")
    print("=" * 70)
    
    demos = [
        ("Basic Webcam", demo_basic_webcam),
        ("Video File", demo_video_file),
        ("Threaded Mode", demo_threaded_mode),
        ("Custom Resolution", demo_custom_resolution),
        ("Frame Generator", demo_frame_generator),
    ]
    
    print("\nAvailable demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  0. Run all demos")
    
    try:
        choice = input("\nSelect demo (0-5): ").strip()
        
        if choice == "0":
            for name, demo_func in demos:
                try:
                    demo_func()
                except Exception as e:
                    print(f"Error in {name}: {e}")
                    continue
        elif choice.isdigit() and 1 <= int(choice) <= len(demos):
            demos[int(choice) - 1][1]()
        else:
            print("Invalid choice")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
    
    print("\n" + "=" * 70)
    print("Demo completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
