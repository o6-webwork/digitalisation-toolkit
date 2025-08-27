# Digitalisation Toolkit

## Usage

1. Download Docling model folder from

Make sure git-lfs is installed (https://git-lfs.com)
```
git lfs install
```
```
cd backend
git clone https://huggingface.co/ds4sd/docling-models
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

## vllm
### SEA-LION
- Download [Gemma2 9B CPT SEA-LIONv3 Instruct](https://huggingface.co/aisingapore/Gemma-SEA-LION-v3-9B-IT).
- Copy the model into the `models` directory. The path is `./models/Gemma-SEA-LION-v3-9B-IT`.

### QWEN2.5
- Download [Qwen2.5 Coder 14B Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct).
- Copy the model into the `models` directory. The path is `./models/Qwen2.5-Coder-14B-Instruct`.

