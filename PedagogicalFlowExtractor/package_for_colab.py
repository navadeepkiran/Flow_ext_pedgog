"""Package PedagogicalFlowExtractor for Google Colab deployment.

Creates a ZIP archive with all necessary files for running the full
Streamlit UI in Google Colab.
"""

import os
import zipfile
from pathlib import Path

def create_colab_package():
    """Create deployment package for Colab."""
    
    print("📦 Packaging PedagogicalFlowExtractor for Google Colab...")
    print()
    
    # Get project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Output file
    zip_path = project_root / "PedagogicalFlowExtractor_Colab.zip"
    
    # Remove old archive
    if zip_path.exists():
        zip_path.unlink()
    
    print("Creating ZIP archive...")
    
    # Files to include
    include_patterns = [
        'pipeline/**/*.py',
        'utils/**/*.py',
        'visualization/**/*.py',
        'app/**/*.py',
        'data/*.json',
        'config.yaml',
        'requirements.txt',
        'README.md',
    ]
    
    # Files to exclude
    exclude_patterns = [
        '__pycache__',
        '*.pyc',
        '*.pyo',
        '.pytest_cache',
        '*.egg-info',
    ]
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        file_count = 0
        
        # Add pipeline modules
        for pattern in include_patterns:
            for file_path in project_root.glob(pattern):
                if file_path.is_file():
                    # Skip excluded patterns
                    if any(excl in str(file_path) for excl in exclude_patterns):
                        continue
                    
                    arc_name = file_path.relative_to(project_root)
                    zipf.write(file_path, arc_name)
                    file_count += 1
                    print(f"  ✓ {arc_name}")
    
    # Get file size
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    
    print()
    print(f"✅ Package created: {zip_path.name} ({size_mb:.2f} MB)")
    print(f"   Contains {file_count} files")
    print()
    print("📤 Next steps:")
    print("  1. Open PedagogicalKG_Complete_Colab.ipynb in Google Colab")
    print("  2. Upload this ZIP file when prompted")
    print("  3. The notebook will extract and launch Streamlit automatically")
    print("  4. Access your app via the public ngrok URL")
    print()
    print("🌐 Or upload to Google Drive for easier repeated access")
    print()

if __name__ == "__main__":
    create_colab_package()
