#!/usr/bin/env python3
"""
Data Drift Simulation Script

Generates synthetic images with intentional drift patterns:
- Brightness drift (gradual increase in pixel intensity)
- Blur drift (progressive blur applied to images)
- Color drift (color channel shifts)
- Combination drift (multiple drift types)

This simulates real-world data drift like camera degradation,
lighting changes, or lens focus issues.
"""

import os
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Tuple, List

# Try to import cv2, but provide fallback
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️ Warning: OpenCV not available. Install with: pip install opencv-python")
    print("   Using numpy-only image generation (limited functionality)")


def create_synthetic_baseline(
    width: int = 640,
    height: int = 480,
    num_images: int = 5,
    seed: int = 42
) -> np.ndarray:
    """Create baseline synthetic images with grid pattern."""
    np.random.seed(seed)
    images = []
    
    for i in range(num_images):
        # Create grid pattern with some variation
        img = np.ones((height, width, 3), dtype=np.uint8) * 50
        
        # Add grid lines
        for y in range(0, height, 60):
            img[y:y+2, :] = 150
        for x in range(0, width, 80):
            img[:, x:x+2] = 150
        
        # Add some noise for realism
        noise = np.random.randint(-20, 20, img.shape, dtype=np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        images.append(img)
    
    return np.array(images)


def apply_brightness_drift(
    images: np.ndarray,
    drift_rate: float = 0.02
) -> Tuple[np.ndarray, List[float]]:
    """Apply progressive brightness increase to simulate drift."""
    drifted_images = []
    brightness_factors = []
    
    for i, img in enumerate(images):
        # Gradually increase brightness
        factor = 1.0 + (drift_rate * i)
        brightness_factors.append(factor)
        
        # Apply brightness adjustment
        drifted = np.clip(img.astype(np.float32) * factor, 0, 255).astype(np.uint8)
        drifted_images.append(drifted)
    
    return np.array(drifted_images), brightness_factors


def apply_blur_drift(
    images: np.ndarray,
    max_kernel: int = 15
) -> Tuple[np.ndarray, List[int]]:
    """Apply progressive blur to simulate focus drift."""
    if not CV2_AVAILABLE:
        print("⚠️ Blur drift requires OpenCV. Returning original images.")
        return images, []
    
    drifted_images = []
    blur_kernels = []
    
    for i, img in enumerate(images):
        # Progressively increase blur kernel size
        kernel_size = 3 + (i * 2)
        kernel_size = min(kernel_size, max_kernel)
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        blur_kernels.append(kernel_size)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)
        drifted_images.append(blurred)
    
    return np.array(drifted_images), blur_kernels


def apply_color_drift(
    images: np.ndarray,
    channel_shift: Tuple[int, int, int] = (5, 10, 15)
) -> Tuple[np.ndarray, Tuple[int, int, int]]:
    """Apply color channel shifts to simulate sensor drift."""
    drifted_images = []
    
    for img in images:
        # Shift color channels (BGR in OpenCV, but we use RGB-like here)
        shifted = img.copy().astype(np.int16)
        shifted[:, :, 0] = np.clip(shifted[:, :, 0] + channel_shift[0], 0, 255)  # Blue
        shifted[:, :, 1] = np.clip(shifted[:, :, 1] + channel_shift[1], 0, 255)  # Green
        shifted[:, :, 2] = np.clip(shifted[:, :, 2] + channel_shift[2], 0, 255)  # Red
        
        drifted_images.append(shifted.astype(np.uint8))
    
    return np.array(drifted_images), channel_shift


def apply_noise_drift(
    images: np.ndarray,
    noise_scale: float = 0.02
) -> Tuple[np.ndarray, List[float]]:
    """Apply progressive noise increase to simulate sensor degradation."""
    drifted_images = []
    noise_levels = []
    
    for i, img in enumerate(images):
        # Increase noise with each image
        noise_level = noise_scale * (i + 1)
        noise_levels.append(noise_level)
        
        # Add Gaussian noise
        noise = np.random.normal(0, noise_level * 255, img.shape)
        noisy = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        drifted_images.append(noisy)
    
    return np.array(drifted_images), noise_levels


def save_images(images: np.ndarray, output_dir: str, prefix: str = "img"):
    """Save images to disk."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    saved_files = []
    
    for i, img in enumerate(images):
        if CV2_AVAILABLE:
            filepath = os.path.join(output_dir, f"{prefix}_{i:03d}.png")
            cv2.imwrite(filepath, img)
        else:
            # Use numpy to save as raw binary
            filepath = os.path.join(output_dir, f"{prefix}_{i:03d}.npy")
            np.save(filepath, img)
        
        saved_files.append(filepath)
    
    return saved_files


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Simulate data drift with synthetic images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate brightness drift
  python simulate_drift.py --drift-type brightness --output ./baseline ./drifted
  
  # Generate blur drift
  python simulate_drift.py --drift-type blur --output ./baseline ./drifted
  
  # Generate all drift types
  python simulate_drift.py --drift-type all --output ./baseline ./drifted
  
  # Custom number of images
  python simulate_drift.py --drift-type brightness --num-images 20 --output ./baseline ./drifted
        """
    )
    
    parser.add_argument(
        "--drift-type",
        choices=["brightness", "blur", "color", "noise", "all"],
        default="all",
        help="Type of drift to simulate"
    )
    
    parser.add_argument(
        "--num-images",
        type=int,
        default=10,
        help="Number of images to generate"
    )
    
    parser.add_argument(
        "--width",
        type=int,
        default=640,
        help="Image width"
    )
    
    parser.add_argument(
        "--height",
        type=int,
        default=480,
        help="Image height"
    )
    
    parser.add_argument(
        "--output",
        nargs=2,
        default=["./baseline_images", "./drifted_images"],
        help="Output directories for baseline and drifted images"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    baseline_dir, drifted_dir = args.output
    
    print("\n" + "=" * 80)
    print("Data Drift Simulation")
    print("=" * 80)
    print(f"Drift Type(s): {args.drift_type}")
    print(f"Number of Images: {args.num_images}")
    print(f"Image Size: {args.width}x{args.height}")
    print(f"Baseline Dir: {baseline_dir}")
    print(f"Drifted Dir: {drifted_dir}")
    print()
    
    # Generate baseline images
    print("Step 1: Generating baseline images...")
    baseline_images = create_synthetic_baseline(
        width=args.width,
        height=args.height,
        num_images=args.num_images,
        seed=args.seed
    )
    baseline_files = save_images(baseline_images, baseline_dir, "baseline")
    print(f"  ✓ Saved {len(baseline_files)} baseline images")
    if args.verbose:
        for f in baseline_files[:2]:
            print(f"    - {f}")
        if len(baseline_files) > 2:
            print(f"    ... and {len(baseline_files) - 2} more")
    
    # Generate drifted images
    print("\nStep 2: Generating drifted images...")
    
    if args.drift_type in ["all", "brightness"]:
        print("  • Brightness drift:")
        drifted, factors = apply_brightness_drift(baseline_images, drift_rate=0.05)
        brightness_files = save_images(drifted, drifted_dir, "brightness_drift")
        print(f"    ✓ Saved {len(brightness_files)} brightness-drifted images")
        if args.verbose:
            print(f"    Brightness factors: {[f'{f:.2f}' for f in factors[:3]]}...")
    
    if args.drift_type in ["all", "blur"]:
        print("  • Blur drift:")
        drifted, kernels = apply_blur_drift(baseline_images, max_kernel=15)
        if len(kernels) > 0:
            blur_files = save_images(drifted, drifted_dir, "blur_drift")
            print(f"    ✓ Saved {len(blur_files)} blur-drifted images")
            if args.verbose:
                print(f"    Blur kernels: {kernels[:5]}...")
        else:
            print("    ✗ Blur drift requires OpenCV")
    
    if args.drift_type in ["all", "color"]:
        print("  • Color drift:")
        drifted, shift = apply_color_drift(baseline_images, channel_shift=(5, 10, 15))
        color_files = save_images(drifted, drifted_dir, "color_drift")
        print(f"    ✓ Saved {len(color_files)} color-drifted images")
        if args.verbose:
            print(f"    Channel shift (B,G,R): {shift}")
    
    if args.drift_type in ["all", "noise"]:
        print("  • Noise drift:")
        drifted, levels = apply_noise_drift(baseline_images, noise_scale=0.02)
        noise_files = save_images(drifted, drifted_dir, "noise_drift")
        print(f"    ✓ Saved {len(noise_files)} noise-drifted images")
        if args.verbose:
            print(f"    Noise levels: {[f'{l:.3f}' for l in levels[:3]]}...")
    
    print("\n" + "=" * 80)
    print("✓ Drift simulation complete!")
    print("=" * 80)
    print(f"\nBaseline images: {baseline_dir}/")
    print(f"Drifted images: {drifted_dir}/")
    print(f"\nNext step: Run drift detection")
    print("  python scripts/detect_drift.py --baseline {} --drifted {}".format(
        baseline_dir, drifted_dir
    ))
    print()
    
    return 0


if __name__ == "__main__":
    exit(main())
