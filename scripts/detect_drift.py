#!/usr/bin/env python3
"""
Data Drift Detection Script

Detects drift in image data by comparing baseline and drifted datasets using:
- Brightness statistics (mean, std of pixel intensity)
- Blur detection (Laplacian variance)
- Color distribution analysis (histogram comparison)
- Statistical tests (Kolmogorov-Smirnov, t-test)

Returns drift scores and alerts if significant drift is detected.
"""

import os
import argparse
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any
from scipy import stats

# Try to import cv2
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class DriftDetector:
    """Detects data drift in images."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.baseline_features = None
        self.drifted_features = None
        self.drift_scores = {}
    
    def load_images(self, directory: str) -> Tuple[List[np.ndarray], List[str]]:
        """Load images from directory."""
        images = []
        filenames = []
        
        image_exts = {'.png', '.jpg', '.jpeg', '.npy', '.bmp'}
        
        for filepath in sorted(Path(directory).iterdir()):
            if filepath.suffix.lower() not in image_exts:
                continue
            
            try:
                if filepath.suffix.lower() == '.npy':
                    img = np.load(filepath)
                elif CV2_AVAILABLE:
                    img = cv2.imread(str(filepath))
                    if img is None:
                        continue
                else:
                    print(f"⚠️ Cannot load {filepath.name} without OpenCV")
                    continue
                
                images.append(img)
                filenames.append(filepath.name)
            except Exception as e:
                print(f"⚠️ Error loading {filepath.name}: {e}")
        
        return images, filenames
    
    def calculate_brightness(self, img: np.ndarray) -> Dict[str, float]:
        """Calculate brightness statistics."""
        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if CV2_AVAILABLE else np.mean(img, axis=2)
        else:
            gray = img
        
        return {
            "mean": float(np.mean(gray)),
            "std": float(np.std(gray)),
            "min": float(np.min(gray)),
            "max": float(np.max(gray)),
            "median": float(np.median(gray))
        }
    
    def calculate_blur(self, img: np.ndarray) -> float:
        """Calculate blur score using Laplacian variance."""
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if CV2_AVAILABLE else np.mean(img, axis=2)
        else:
            gray = img
        
        if CV2_AVAILABLE:
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        else:
            # Simple edge detection without cv2
            laplacian = np.abs(np.diff(gray, axis=0)) + np.abs(np.diff(gray, axis=1))
        
        blur_score = float(np.var(laplacian))
        return blur_score
    
    def calculate_color_histogram(self, img: np.ndarray) -> np.ndarray:
        """Calculate color histogram for comparison."""
        if len(img.shape) == 3:
            # Process each channel
            channels = cv2.split(img) if CV2_AVAILABLE else [img[:,:,i] for i in range(3)]
        else:
            channels = [img]
        
        hist_all = []
        for channel in channels:
            hist = np.histogram(channel, bins=32, range=(0, 256))[0]
            # Normalize histogram
            hist = hist / (hist.sum() + 1e-6)
            hist_all.append(hist)
        
        return np.concatenate(hist_all)
    
    def extract_features(self, images: List[np.ndarray]) -> Dict[str, Any]:
        """Extract features from a set of images."""
        features = {
            "brightness": [],
            "blur": [],
            "histograms": []
        }
        
        for img in images:
            features["brightness"].append(self.calculate_brightness(img))
            features["blur"].append(self.calculate_blur(img))
            features["histograms"].append(self.calculate_color_histogram(img))
        
        return features
    
    def calculate_drift_score(
        self,
        baseline_features: Dict[str, Any],
        drifted_features: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate drift scores between baseline and drifted data."""
        scores = {}
        
        # Brightness drift: compare mean brightness
        baseline_brightness = np.array([f["mean"] for f in baseline_features["brightness"]])
        drifted_brightness = np.array([f["mean"] for f in drifted_features["brightness"]])
        
        brightness_diff = np.abs(np.mean(drifted_brightness) - np.mean(baseline_brightness))
        scores["brightness_drift"] = float(brightness_diff)
        
        # T-test for brightness
        t_stat, p_value = stats.ttest_ind(baseline_brightness, drifted_brightness)
        scores["brightness_p_value"] = float(p_value)
        
        # Blur drift: compare blur variance
        baseline_blur = np.array(baseline_features["blur"])
        drifted_blur = np.array(drifted_features["blur"])
        
        blur_diff = np.abs(np.mean(drifted_blur) - np.mean(baseline_blur))
        scores["blur_drift"] = float(blur_diff)
        
        # T-test for blur
        t_stat_blur, p_value_blur = stats.ttest_ind(baseline_blur, drifted_blur)
        scores["blur_p_value"] = float(p_value_blur)
        
        # Histogram drift: compare color distributions (Wasserstein distance)
        baseline_hist = np.mean(baseline_features["histograms"], axis=0)
        drifted_hist = np.mean(drifted_features["histograms"], axis=0)
        
        # Chi-square distance
        chi_square = float(np.sum((baseline_hist - drifted_hist) ** 2 / (baseline_hist + drifted_hist + 1e-6)))
        scores["histogram_drift"] = chi_square
        
        # Kolmogorov-Smirnov test on histograms
        ks_stat, ks_p = stats.ks_2samp(baseline_hist, drifted_hist)
        scores["histogram_p_value"] = float(ks_p)
        
        # Overall drift score (normalized)
        overall_score = (
            scores["brightness_drift"] / 100 +  # Normalize to 0-1 range
            scores["blur_drift"] / 1000 +        # Normalize
            scores["histogram_drift"] / 100      # Normalize
        ) / 3.0
        
        scores["overall_drift_score"] = float(overall_score)
        
        return scores
    
    def analyze(self, baseline_dir: str, drifted_dir: str) -> Dict[str, Any]:
        """Analyze drift between baseline and drifted datasets."""
        print("\n" + "=" * 80)
        print("Data Drift Detection")
        print("=" * 80)
        
        # Load images
        print("\nStep 1: Loading images...")
        baseline_images, baseline_files = self.load_images(baseline_dir)
        drifted_images, drifted_files = self.load_images(drifted_dir)
        
        print(f"  ✓ Loaded {len(baseline_images)} baseline images")
        print(f"  ✓ Loaded {len(drifted_images)} drifted images")
        
        if len(baseline_images) == 0 or len(drifted_images) == 0:
            print("  ✗ Error: Could not load images")
            return None
        
        # Extract features
        print("\nStep 2: Extracting features...")
        baseline_features = self.extract_features(baseline_images)
        drifted_features = self.extract_features(drifted_images)
        print("  ✓ Features extracted")
        
        # Calculate drift scores
        print("\nStep 3: Calculating drift scores...")
        drift_scores = self.calculate_drift_score(baseline_features, drifted_features)
        print("  ✓ Drift scores calculated")
        
        # Create results
        results = {
            "baseline_dir": baseline_dir,
            "drifted_dir": drifted_dir,
            "baseline_images": len(baseline_images),
            "drifted_images": len(drifted_images),
            "drift_scores": drift_scores,
            "timestamp": str(datetime.now())
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]) -> None:
        """Print drift detection results."""
        if results is None:
            return
        
        print("\n" + "=" * 80)
        print("Drift Detection Results")
        print("=" * 80)
        
        # Drift scores summary
        print("\nDrift Scores:")
        scores = results["drift_scores"]
        
        print(f"  Brightness Drift: {scores['brightness_drift']:.2f}")
        print(f"    P-value: {scores['brightness_p_value']:.4f} {'*' if scores['brightness_p_value'] < 0.05 else ''}")
        
        print(f"  Blur Drift: {scores['blur_drift']:.2f}")
        print(f"    P-value: {scores['blur_p_value']:.4f} {'*' if scores['blur_p_value'] < 0.05 else ''}")
        
        print(f"  Histogram Drift (Chi-square): {scores['histogram_drift']:.4f}")
        print(f"    P-value: {scores['histogram_p_value']:.4f} {'*' if scores['histogram_p_value'] < 0.05 else ''}")
        
        print(f"\n  Overall Drift Score: {scores['overall_drift_score']:.4f}")
        
        # Interpretation
        print("\n" + "-" * 80)
        print("Interpretation:")
        overall = scores["overall_drift_score"]
        
        if overall < 0.1:
            print("  ✓ No significant drift detected (score < 0.1)")
        elif overall < 0.3:
            print("  ⚠️ Mild drift detected (score 0.1-0.3)")
        elif overall < 0.7:
            print("  ⚠️ Moderate drift detected (score 0.3-0.7)")
        else:
            print("  ✗ Severe drift detected (score > 0.7)")
        
        # Statistical significance
        print("\nStatistical Significance (* = p < 0.05):")
        if scores["brightness_p_value"] < 0.05:
            print(f"  * Brightness has significantly changed (p={scores['brightness_p_value']:.4f})")
        if scores["blur_p_value"] < 0.05:
            print(f"  * Blur characteristics have significantly changed (p={scores['blur_p_value']:.4f})")
        if scores["histogram_p_value"] < 0.05:
            print(f"  * Color distribution has significantly changed (p={scores['histogram_p_value']:.4f})")
        
        print("\n" + "=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Detect data drift in images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Detect drift between baseline and drifted images
  python detect_drift.py --baseline ./baseline_images --drifted ./drifted_images
  
  # Output results to JSON
  python detect_drift.py --baseline ./baseline_images --drifted ./drifted_images --output results.json
  
  # Verbose output
  python detect_drift.py --baseline ./baseline_images --drifted ./drifted_images --verbose
        """
    )
    
    parser.add_argument(
        "--baseline",
        required=True,
        help="Directory with baseline images"
    )
    
    parser.add_argument(
        "--drifted",
        required=True,
        help="Directory with drifted images"
    )
    
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file for results"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    # Create detector
    detector = DriftDetector(verbose=args.verbose)
    
    # Analyze
    results = detector.analyze(args.baseline, args.drifted)
    
    if results:
        # Print results
        detector.print_results(results)
        
        # Save to JSON if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n✓ Results saved to {args.output}")
    
    return 0


if __name__ == "__main__":
    from datetime import datetime
    exit(main())
