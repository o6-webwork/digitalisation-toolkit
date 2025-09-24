# Digitalisation Toolkit

## Prerequisites

**CUDA Compatibility**: Before building the Docker containers, verify that your GPU and CUDA drivers are compatible with CUDA 12.1 (cu121), which is specified in `backend/Dockerfile` line 7. If your system uses a different CUDA version, you may need to update the PyTorch installation URL in the Dockerfile accordingly.

## Usage

1. Download Docling model folder from

Make sure git-lfs is installed (https://git-lfs.com)
```
git lfs install
```
```
cd backend
git clone https://huggingface.co/ds4sd/docling-models
cd docling-models
git checkout 094b693
```

2. Download the following zip files from

    >   https://www.jaided.ai/easyocr/modelhub/

```
2rd Generation Models
english_g2
latin_g2
zh_sim_g2 

Text Detection Models
CRAFT
```
unzip them and save the 4 .pth files in the `backend/EasyOcr` folder.

3.  Build the Docker image:
```bash
docker compose build
```

4.  Run image
```bash
docker compose up -d
```

## System Configuration

The application is configured with the following limits to handle large document processing:

- **Processing Timeout**: 4 hours (14,400 seconds) for long-running operations
- **File Upload Limit**: 5GB maximum file size
- **Request Timeout**: Extended timeouts for PDF translation and document processing

These settings are optimized for processing large PDFs and complex documents that may require significant processing time.

## Offline Deployment

For environments without internet access, you can create Docker image tar files for offline deployment:

### Creating Tar Files

1. **Automated approach**: Run the provided script:
```bash
./create-tar-files.sh
```

2. **Manual approach**:
```bash
# Build and tag images
docker compose build
docker tag digitalisation-toolkit-digitalisation_toolkit-frontend:latest digitalisation-toolkit-frontend:latest
docker tag digitalisation-toolkit-digitalisation_toolkit-backend:latest digitalisation-toolkit-backend:latest

# Create tar files
mkdir -p tar-files
docker save digitalisation-toolkit-frontend:latest -o tar-files/digitalisation-toolkit-frontend.tar
docker save digitalisation-toolkit-backend:latest -o tar-files/digitalisation-toolkit-backend.tar
docker save nginx:1.27.2-alpine -o tar-files/nginx-1.27.2-alpine.tar
```

### Using Tar Files in Offline Environment

1. **Copy the tar-files directory** to your offline environment
2. **Load the images**:
```bash
docker load -i tar-files/digitalisation-toolkit-frontend.tar
docker load -i tar-files/digitalisation-toolkit-backend.tar
docker load -i tar-files/nginx-1.27.2-alpine.tar
```
3. **Run with offline compose file**:
```bash
docker compose -f docker-compose.offline.yml up -d
```

The `docker-compose.offline.yml` file uses pre-built images instead of building from source, making it suitable for offline deployment.
