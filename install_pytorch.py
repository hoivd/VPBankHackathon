#!/usr/bin/env python3
"""
Script to install PyTorch with the correct CUDA version
"""
import os
import platform
import subprocess
import sys

def get_cuda_version():
    """Try to detect CUDA version installed on the system"""
    try:
        # Try to run nvcc --version
        result = subprocess.run(['nvcc', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            # Extract version from output like "Cuda compilation tools, release 11.7, V11.7.99"
            for line in result.stdout.split('\n'):
                if 'release' in line:
                    version_str = line.split('release')[1].strip().split(',')[0]
                    major_minor = version_str.split('.')
                    if len(major_minor) >= 2:
                        return f"{major_minor[0]}{major_minor[1]}"
    except:
        pass
    
    # If nvcc detection failed, try checking for CUDA_HOME or CUDA_PATH
    for env_var in ['CUDA_HOME', 'CUDA_PATH']:
        cuda_path = os.environ.get(env_var)
        if cuda_path:
            # Try to extract version from path like C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7
            if 'v' in cuda_path:
                version_str = cuda_path.split('v')[-1].split('\\')[0].split('/')[0]
                major_minor = version_str.split('.')
                if len(major_minor) >= 2:
                    return f"{major_minor[0]}{major_minor[1]}"
    
    return None

def install_pytorch():
    """Install PyTorch with the correct CUDA version"""
    # Detect OS
    os_name = platform.system().lower()
    
    # Detect CUDA version
    cuda_version = get_cuda_version()
    
    print(f"Detected OS: {os_name}")
    print(f"Detected CUDA version: {cuda_version or 'Not found'}")
    
    # Default to CPU version if CUDA not found
    cuda_suffix = ""
    if cuda_version:
        cuda_suffix = f"+cu{cuda_version}"
    
    # PyTorch versions to install
    torch_version = "2.5.1"
    torchvision_version = "0.20.1"
    torchaudio_version = "2.5.1"
    
    # Construct install command
    if os_name == "windows":
        install_cmd = f"pip install torch=={torch_version}{cuda_suffix} torchvision=={torchvision_version}{cuda_suffix} torchaudio=={torchaudio_version}{cuda_suffix} --index-url https://download.pytorch.org/whl/cu121"
    else:
        # Linux/Mac - try the standard PyTorch install command
        install_cmd = f"pip install torch=={torch_version}{cuda_suffix} torchvision=={torchvision_version}{cuda_suffix} torchaudio=={torchaudio_version}{cuda_suffix} --index-url https://download.pytorch.org/whl/cu121"
    
    print(f"Running: {install_cmd}")
    
    # Execute the installation command
    os.system(install_cmd)
    
    # Install other requirements
    print("\nInstalling other requirements...")
    os.system("pip install -r requirements.txt")

if __name__ == "__main__":
    install_pytorch()
    print("\nInstallation complete. Please verify PyTorch installation:")
    print("python -c \"import torch; print('CUDA available:', torch.cuda.is_available())\"") 