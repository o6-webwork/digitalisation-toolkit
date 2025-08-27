# Issues
## Docling performace
Docling runs much longer than expected
### Suspected Issues
1. ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
torchaudio 2.5.1+cu121 requires torch==2.5.1, but you have torch 2.4.0 which is incompatible.
2. This error occurs because the custom kernel for MultiScaleDeformableAttention failed to build. The root cause seems to be related to the ninja build tool or a syntax issue in the shell environment.
### Fixes

1. Install torch==2.5.1

2. sudo apt-get install build-essential ninja-build cmake
OR
sudo apt update
sudo apt install build-essential cmake gcc g++ -y

### New Issue
Could not load the custom kernel for multi-scale deformable attention: Unknown CUDA arch (6.8) or GPU not supported
/home/ubuntu/Desktop/Mini_RAG/structured_extraction/venv/lib/python3.12/site-packages/torch/nn/parallel/parallel_apply.py:79: FutureWarning: `torch.cuda.amp.autocast(args...)` is deprecated. Please use `torch.amp.autocast('cuda', args...)` instead.
with torch.cuda.device(device), torch.cuda.stream(stream), autocast(enabled=autocast_enabled):