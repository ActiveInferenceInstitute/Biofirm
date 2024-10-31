"""
Startup script for Biofirm package - handles dependencies and core imports.
Creates and manages a virtual environment for isolated package management.
"""
import subprocess
import sys
import os
import venv
import shutil
from pathlib import Path

# Required packages for the project
REQUIRED_PACKAGES = [
    'numpy==1.23.5',  # Specific version for pymdp compatibility
    'pandas',
    'matplotlib',
    'colorama',  # Added for colored logging
    'inferactively-pymdp==0.0.7.1',
    'typing-extensions',
    'dataclasses;python_version<"3.7"'
]

def clear_venv():
    """Remove existing virtual environment if it exists."""
    venv_path = Path("venv")
    if venv_path.exists():
        print("Removing existing virtual environment...")
        shutil.rmtree(venv_path)

def create_venv():
    """Create a virtual environment if it doesn't exist."""
    venv_path = Path("venv")
    if not venv_path.exists():
        print("Creating virtual environment...")
        venv.create(venv_path, with_pip=True)
    return venv_path

def get_venv_pip():
    """Get the path to the virtual environment's pip executable."""
    if sys.platform == "win32":
        return Path("venv/Scripts/pip.exe")
    return Path("venv/bin/pip")

def install_dependencies():
    """Install required packages in the virtual environment."""
    pip_path = get_venv_pip()
    
    # First upgrade pip
    try:
        print("Upgrading pip...")
        subprocess.check_call([str(pip_path), 'install', '--upgrade', 'pip'])
    except subprocess.CalledProcessError as e:
        print(f"Error upgrading pip: {e}")
        return False
    
    # Install all required packages
    for package in REQUIRED_PACKAGES:
        try:
            print(f"Installing {package}...")
            subprocess.check_call([str(pip_path), 'install', package])
        except subprocess.CalledProcessError as e:
            print(f"Error installing {package}: {e}")
            return False
    
    return True

def setup_environment():
    """Set up the virtual environment."""
    clear_venv()
    create_venv()
    if not install_dependencies():
        print("Failed to install dependencies")
        return False
    
    # Add the virtual environment's site-packages to sys.path
    venv_path = Path("venv")
    if sys.platform == "win32":
        site_packages = venv_path / "Lib" / "site-packages"
    else:
        site_packages = venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    
    sys.path.insert(0, str(site_packages))
    return True

def test_imports():
    """Test importing required packages and print versions."""
    try:
        # Core imports
        import numpy as np
        print(f"✓ numpy {np.__version__}")
        
        import pandas as pd
        print(f"✓ pandas {pd.__version__}")
        
        import matplotlib
        print(f"✓ matplotlib {matplotlib.__version__}")
        
        import colorama
        print(f"✓ colorama {colorama.__version__}")
        
        # PyMDP imports
        import pymdp
        from pymdp.agent import Agent
        from pymdp import utils
        print("✓ pymdp imported successfully")
        
        # Test PyMDP functionality
        A = utils.random_A_matrix(8, 8)
        print("✓ PyMDP core functions working")
        
        # Set random seed
        np.random.seed(0)
        print("✓ random seed set")
        
        return True
        
    except ImportError as e:
        print(f"\nError importing packages: {e}")
        return False
    except Exception as e:
        print(f"\nError during testing: {e}")
        return False

def activate_venv():
    """Generate the appropriate activation command based on the platform."""
    if sys.platform == "win32":
        activate_cmd = "venv\\Scripts\\activate"
    else:
        activate_cmd = "source venv/bin/activate"
    
    print("\nTo activate the virtual environment, run:")
    print(f"{activate_cmd}")

if __name__ == "__main__":
    try:
        print("\nSetting up Biofirm environment...")
        if setup_environment():
            success = test_imports()
            if success:
                print("\nEnvironment setup complete!")
                activate_venv()
            else:
                print("\nEnvironment setup completed with errors.")
                print("Please check the error messages above and try again if needed.")
        else:
            print("\nFailed to setup environment")
            sys.exit(1)
    except Exception as e:
        print(f"\nSetup failed: {e}")
        sys.exit(1)