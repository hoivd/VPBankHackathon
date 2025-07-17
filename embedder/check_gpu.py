import torch

def check_gpu():
    print("🚀 PyTorch version:", torch.__version__)
    if torch.cuda.is_available():
        print("✅ CUDA is available!")
        print("🖥️ GPU count:", torch.cuda.device_count())
        print("🧠 GPU name:", torch.cuda.get_device_name(0))
        print("⚡ CUDA version:", torch.version.cuda)
    else:
        print("❌ CUDA is NOT available. Running on CPU.")

if __name__ == "__main__":
    check_gpu()