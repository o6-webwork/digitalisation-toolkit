# Outstanding Issues

## Docling Performance Issues
Docling has an issue where subsequent use results in longer processing time for certain devices. Some fixes are available but the problem may recur.

### Known Issues
1. **Dependency Conflicts**: pip's dependency resolver conflicts between torch versions
   ```
   ERROR: torchaudio 2.5.1+cu121 requires torch==2.5.1, but you have torch 2.4.0 which is incompatible.
   ```

2. **Custom Kernel Build Failure**: MultiScaleDeformableAttention kernel fails to build due to ninja build tool or shell syntax issues

3. **CUDA Architecture Compatibility**:
   ```
   Could not load the custom kernel for multi-scale deformable attention: Unknown CUDA arch (6.8) or GPU not supported
   ```

4. **Deprecation Warnings**:
   ```
   torch.cuda.amp.autocast(args...) is deprecated. Please use torch.amp.autocast('cuda', args...) instead.
   ```

### Potential Solutions

1. **Update PyTorch** (may require updating other libraries as current version is 2.4.0):
   ```bash
   pip install torch==2.5.1
   ```

2. **Install Build Tools**:
   ```bash
   sudo apt-get install build-essential ninja-build cmake
   ```
   OR
   ```bash
   sudo apt update
   sudo apt install build-essential cmake gcc g++ -y
   ```

3. **Temporary Performance Fix**:
   ```bash
   top
   ```
   Running `top` in terminal seems to temporarily fix extended processing times.
