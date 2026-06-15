#!/usr/bin/env python3
"""
Download UGRansome dataset from Kaggle.
Requires: kaggle API credentials (~/.kaggle/kaggle.json)
"""

import os
import sys
from pathlib import Path

def main():
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data" / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("QZero - Dataset Download")
    print("=" * 60)
    
    # Check for kaggle credentials
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        print("\n⚠️  Kaggle API credentials not found!")
        print("\nTo download the dataset:")
        print("1. Go to https://www.kaggle.com/settings")
        print("2. Click 'Create New API Token'")
        print("3. Save kaggle.json to ~/.kaggle/kaggle.json")
        print("4. Run: chmod 600 ~/.kaggle/kaggle.json")
        print("\nOr download manually from:")
        print("https://www.kaggle.com/datasets/nkongolo/ugransome-dataset")
        print(f"\nPlace the CSV files in: {data_dir}")
        return 1
    
    try:
        import kaggle
        print("\n📥 Downloading UGRansome dataset...")
        kaggle.api.dataset_download_files(
            "nkongolo/ugransome-dataset",
            path=str(data_dir),
            unzip=True
        )
        print(f"✅ Dataset downloaded to: {data_dir}")
        
        # List downloaded files
        print("\n📁 Downloaded files:")
        for f in data_dir.iterdir():
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"   - {f.name} ({size_mb:.2f} MB)")
        
        return 0
        
    except ImportError:
        print("\n❌ Kaggle package not installed.")
        print("Run: pip install kaggle")
        return 1
    except Exception as e:
        print(f"\n❌ Error downloading dataset: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
