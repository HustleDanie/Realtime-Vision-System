"""
Quick runner script for the fake detection test.

This provides a simple interface to run the test with various options.

Usage:
    python tests/run_fake_detection_test.py
    python tests/run_fake_detection_test.py --count 20
    python tests/run_fake_detection_test.py --count 5 --cleanup
"""

import argparse
import sys
from pathlib import Path
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_fake_detections import DetectionTestSuite


def cleanup_test_outputs(test_dir: str = "./test_outputs"):
    """
    Clean up previous test outputs.
    
    Args:
        test_dir: Directory to clean
    """
    test_path = Path(test_dir)
    if test_path.exists():
        print(f"🗑️  Cleaning up previous test outputs at {test_dir}...")
        shutil.rmtree(test_path)
        print(f"✓ Cleaned up {test_dir}")
    else:
        print(f"ℹ️  No previous test outputs to clean (directory doesn't exist)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run fake detection logging test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/run_fake_detection_test.py
  python tests/run_fake_detection_test.py --count 20
  python tests/run_fake_detection_test.py --count 5 --cleanup
  python tests/run_fake_detection_test.py --dir ./my_test_dir
        """
    )
    
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of fake detections to generate (default: 10)"
    )
    
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up previous test outputs before running"
    )
    
    parser.add_argument(
        "--dir",
        type=str,
        default="./test_outputs",
        help="Test output directory (default: ./test_outputs)"
    )
    
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verification steps (faster, for debugging)"
    )
    
    args = parser.parse_args()
    
    # Validate count
    if args.count < 1 or args.count > 1000:
        print("❌ Error: Count must be between 1 and 1000")
        sys.exit(1)
    
    # Cleanup if requested
    if args.cleanup:
        cleanup_test_outputs(args.dir)
        print()
    
    # Create test suite
    print("🔧 Setting up test suite...")
    test_suite = DetectionTestSuite(test_dir=args.dir)
    print("✓ Test suite ready\n")
    
    # Run test
    try:
        if args.no_verify:
            print(f"⚠️  Running in NO-VERIFY mode (generating {args.count} detections only)\n")
            
            print("=" * 70)
            print(f"GENERATING {args.count} FAKE DETECTIONS")
            print("=" * 70)
            
            for i in range(1, args.count + 1):
                test_suite.generate_and_log_detection(i)
            
            print(f"\n✓ Generated {args.count} detections (verification skipped)")
            success = True
        else:
            success = test_suite.run_full_test(num_detections=args.count)
        
        if success:
            print("\n✅ Test completed successfully!")
            print(f"\n📁 Check outputs at: {args.dir}")
            print(f"   - Database: {args.dir}/test_vision_logs.db")
            print(f"   - Images: {args.dir}/test_prediction_images/")
            sys.exit(0)
        else:
            print("\n❌ Test completed with failures!")
            print(f"   Check error messages above for details")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
