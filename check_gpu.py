import torch

is_cuda_available = torch.cuda.is_available()

print(f"Видеокарта NVIDIA (CUDA) доступна: {is_cuda_available}")

if is_cuda_available:
    print(f"Название видеокарты: {torch.cuda.get_device_name(0)}")