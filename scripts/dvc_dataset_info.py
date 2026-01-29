"""
DVC Dataset Management Script

Shows how to:
1. List all DVC dataset versions from git history
2. Verify current dataset checksum
3. Show dataset status and information

Usage:
    python scripts/dvc_dataset_info.py
    python scripts/dvc_dataset_info.py --dataset dataset.dvc
    python scripts/dvc_dataset_info.py --verify-only
"""

import subprocess
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime


def run_command(cmd, capture_output=True, check=True):
    """Run shell command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            check=check
        )
        return result.stdout.strip() if capture_output else None
    except subprocess.CalledProcessError as e:
        if capture_output:
            print(f"Error: {e.stderr}")
        raise


def list_dvc_versions(dvc_file="dataset.dvc"):
    """
    List all versions of a DVC-tracked dataset from git history.
    
    Args:
        dvc_file: Path to the .dvc file (e.g., 'dataset.dvc')
    """
    print(f"\n{'=' * 70}")
    print(f"DVC DATASET VERSION HISTORY: {dvc_file}")
    print(f"{'=' * 70}\n")
    
    # Check if file exists
    if not Path(dvc_file).exists():
        print(f"❌ Error: {dvc_file} not found")
        print(f"   Current directory: {Path.cwd()}")
        return
    
    # Get git log for the .dvc file
    cmd = f'git log --oneline --date=short --pretty=format:"%h|%ad|%an|%s" {dvc_file}'
    
    try:
        output = run_command(cmd)
        
        if not output:
            print(f"⚠️  No git history found for {dvc_file}")
            print(f"   The file may not be committed to git yet.")
            return
        
        # Parse and display versions
        lines = output.split('\n')
        
        print(f"Found {len(lines)} version(s) in git history:\n")
        
        for i, line in enumerate(lines, 1):
            parts = line.split('|')
            if len(parts) >= 4:
                commit_hash, date, author, message = parts[0], parts[1], parts[2], '|'.join(parts[3:])
                print(f"[{i}] Commit: {commit_hash}")
                print(f"    Date:    {date}")
                print(f"    Author:  {author}")
                print(f"    Message: {message}")
                
                # Get the MD5 hash for this version
                try:
                    md5_cmd = f"git show {commit_hash}:{dvc_file}"
                    dvc_content = run_command(md5_cmd)
                    
                    # Parse the .dvc file content (YAML format)
                    for line in dvc_content.split('\n'):
                        if 'md5:' in line:
                            md5 = line.split('md5:')[1].strip()
                            print(f"    MD5:     {md5}")
                            break
                except:
                    pass
                
                print()
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting git history: {e}")
        print(f"   Make sure git is initialized and {dvc_file} is committed.")


def verify_dataset_checksum(dvc_file="dataset.dvc"):
    """
    Verify the current dataset checksum matches what's recorded in the .dvc file.
    
    Args:
        dvc_file: Path to the .dvc file
    """
    print(f"\n{'=' * 70}")
    print(f"VERIFYING DATASET CHECKSUM: {dvc_file}")
    print(f"{'=' * 70}\n")
    
    # Check if file exists
    if not Path(dvc_file).exists():
        print(f"❌ Error: {dvc_file} not found")
        return False
    
    # Get expected checksum from .dvc file
    print(f"📄 Reading {dvc_file}...")
    
    with open(dvc_file, 'r') as f:
        content = f.read()
        print(f"\n{dvc_file} contents:")
        print("-" * 70)
        print(content)
        print("-" * 70)
    
    # Check DVC status
    print(f"\n🔍 Running DVC status check...")
    
    try:
        status_output = run_command(f"dvc status {dvc_file}", check=False)
        
        if not status_output or status_output == "":
            print(f"✅ Dataset is up to date!")
            print(f"   Current dataset matches the checksum in {dvc_file}")
            return True
        else:
            print(f"⚠️  Dataset status:")
            print(status_output)
            
            if "not in cache" in status_output.lower():
                print(f"\n💡 Tip: Run 'dvc pull' to download the dataset")
            elif "modified" in status_output.lower() or "changed" in status_output.lower():
                print(f"\n⚠️  Dataset has been modified since last commit")
                print(f"   Run 'dvc add {dvc_file.replace('.dvc', '')}' to update")
            
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error checking DVC status: {e}")
        return False


def show_dataset_info(dvc_file="dataset.dvc"):
    """
    Show comprehensive information about the DVC-tracked dataset.
    
    Args:
        dvc_file: Path to the .dvc file
    """
    print(f"\n{'=' * 70}")
    print(f"DVC DATASET INFORMATION: {dvc_file}")
    print(f"{'=' * 70}\n")
    
    # Check if file exists
    if not Path(dvc_file).exists():
        print(f"❌ Error: {dvc_file} not found")
        return
    
    # Get dataset path
    dataset_path = dvc_file.replace('.dvc', '')
    
    print(f"Dataset File: {dvc_file}")
    print(f"Dataset Path: {dataset_path}")
    
    # Check if dataset exists locally
    dataset_exists = Path(dataset_path).exists()
    print(f"Local Status: {'✅ Present' if dataset_exists else '❌ Not present locally'}")
    
    if dataset_exists:
        # Get dataset size
        if Path(dataset_path).is_file():
            size = Path(dataset_path).stat().st_size
            size_mb = size / (1024 * 1024)
            print(f"Dataset Size: {size_mb:.2f} MB ({size:,} bytes)")
        elif Path(dataset_path).is_dir():
            # Count files in directory
            files = list(Path(dataset_path).rglob('*'))
            file_count = len([f for f in files if f.is_file()])
            print(f"Dataset Type: Directory")
            print(f"File Count:   {file_count} files")
    
    # Parse .dvc file for more info
    print(f"\n📋 DVC File Details:")
    try:
        with open(dvc_file, 'r') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    print(f"   {line}")
    except Exception as e:
        print(f"   Error reading file: {e}")


def show_dvc_cache_info():
    """Show DVC cache information."""
    print(f"\n{'=' * 70}")
    print(f"DVC CACHE INFORMATION")
    print(f"{'=' * 70}\n")
    
    try:
        # Get cache directory
        cache_dir = run_command("dvc cache dir")
        print(f"Cache Directory: {cache_dir}")
        
        # Check if cache exists
        if Path(cache_dir).exists():
            # Count cached files
            cache_files = list(Path(cache_dir).rglob('*'))
            file_count = len([f for f in cache_files if f.is_file()])
            print(f"Cached Files:    {file_count}")
            
            # Calculate cache size
            total_size = sum(f.stat().st_size for f in cache_files if f.is_file())
            size_mb = total_size / (1024 * 1024)
            print(f"Cache Size:      {size_mb:.2f} MB")
        else:
            print(f"Cache Status:    Empty (no cached files)")
            
    except Exception as e:
        print(f"Error getting cache info: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DVC Dataset Management - List versions and verify checksums",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show all information (default)
  python scripts/dvc_dataset_info.py
  
  # Verify dataset checksum only
  python scripts/dvc_dataset_info.py --verify-only
  
  # List versions only
  python scripts/dvc_dataset_info.py --versions-only
  
  # Use custom .dvc file
  python scripts/dvc_dataset_info.py --dataset mydata.dvc
        """
    )
    
    parser.add_argument(
        "--dataset",
        type=str,
        default="dataset.dvc",
        help="Path to .dvc file (default: dataset.dvc)"
    )
    
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify checksum, skip other info"
    )
    
    parser.add_argument(
        "--versions-only",
        action="store_true",
        help="Only show version history, skip other info"
    )
    
    parser.add_argument(
        "--info-only",
        action="store_true",
        help="Only show dataset info, skip verification"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("DVC DATASET MANAGEMENT TOOL")
    print("=" * 70)
    
    # Check if git is available
    try:
        run_command("git --version", capture_output=False)
    except:
        print("\n❌ Error: git is not installed or not in PATH")
        sys.exit(1)
    
    # Check if DVC is available
    try:
        run_command("dvc version", capture_output=False)
    except:
        print("\n❌ Error: DVC is not installed or not in PATH")
        print("   Install with: pip install dvc")
        sys.exit(1)
    
    # Execute requested operations
    if args.verify_only:
        verify_dataset_checksum(args.dataset)
    elif args.versions_only:
        list_dvc_versions(args.dataset)
    elif args.info_only:
        show_dataset_info(args.dataset)
    else:
        # Show everything
        show_dataset_info(args.dataset)
        list_dvc_versions(args.dataset)
        verify_dataset_checksum(args.dataset)
        show_dvc_cache_info()
    
    print("\n" + "=" * 70)
    print("✅ COMPLETE")
    print("=" * 70)
    print("\nUseful DVC Commands:")
    print("  dvc pull              - Download dataset from remote storage")
    print("  dvc push              - Upload dataset to remote storage")
    print("  dvc add <path>        - Track new or updated dataset")
    print("  dvc checkout          - Restore dataset to version in .dvc file")
    print("  dvc status            - Check if dataset matches .dvc file")
    print("  git log dataset.dvc   - See all dataset version commits")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
