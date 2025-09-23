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
