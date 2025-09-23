# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a PDF digitalization toolkit built as a containerized application with three main components:

- **Frontend**: Streamlit web application (`frontend/`) with multiple pages for different processing tasks
- **Backend**: FastAPI server (`backend/`) providing REST endpoints for document processing
- **Models**: LLM services running via vLLM (`models/` directory)

The application supports PDF translation, text processing, structured inference, and schema generation using various ML models including Docling for document processing and LLMs for text generation.

## Key Components

### Backend (Modular Structure)
- **`main.py`**: Clean FastAPI application with endpoint definitions only (219 lines vs original 637)
- **`config/settings.py`**: Centralized configuration management with environment variables
- **`services/`**: Business logic separated into focused services:
  - `translation_service.py`: Text translation functionality
  - `document_service.py`: PDF processing with Docling integration  
  - `llm_service.py`: LLM interactions for schema generation and structured inference
- **`models/schemas.py`**: Pydantic models for request/response validation
- **`utils/`**: Common utilities:
  - `logger.py`: Structured logging with consistent formatting
  - `api_client.py`: Centralized HTTP client for external API calls

### Frontend (`frontend/streamlitapp.py`) 
- Multi-page Streamlit application with session state management
- Pages located in `frontend/app_pages/` directory:
  - Data Loader
  - Translation (text and PDF)
  - Free Processing  
  - Schema Builder
  - Structured Inference (single and batch)

### Docker Services
- Uses Docker Compose with separate containers for frontend, backend, nginx proxy, and vLLM model services
- Model services include Qwen2.5-Coder-14B-Instruct and Gemma-SEA-LION-v3-9B-IT

## Common Development Commands

### Setup and Dependencies
```bash
# Install git-lfs for model files
git lfs install

# Clone required models
cd backend
git clone https://huggingface.co/ds4sd/docling-models

# Download and place EasyOCR models in backend/EasyOcr/
# Required models: english_g2, latin_g2, zh_sim_g2, CRAFT
```

### Docker Operations
```bash
# Build all services
docker compose build

# Start services in detached mode
docker compose up -d

# Stop services
docker compose down
```

### Environment Configuration
- Backend configuration: `backend/.env` (use `backend/example.env` as template)
- Frontend configuration: `frontend/.env` (use `frontend/example.env` as template)
- Key environment variables:
  - `ARTIFACTS_PATH`: Path to Docling model artifacts
  - `MODEL_STORAGE_DIRECTORY`: Directory for EasyOCR models
  - `VLLM_SEALION_URL` / `VLLM_QWEN2_5_URL`: vLLM service endpoints

## Model Requirements

### Docling Models
- Download from Hugging Face: `ds4sd/docling-models`
- Contains layout detection and tableformer models
- Uses Git LFS for `.safetensors` files

### EasyOCR Models
- Download from jaided.ai/easyocr/modelhub
- Required: english_g2.pth, latin_g2.pth, zh_sim_g2.pth, craft_mlt_25k.pth
- Place in `backend/EasyOcr/` directory

### LLM Models
- Gemma2 9B CPT SEA-LIONv3 Instruct → `./models/Gemma-SEA-LION-v3-9B-IT`
- Qwen2.5 Coder 14B Instruct → `./models/Qwen2.5-Coder-14B-Instruct`

## Code Quality Improvements

The backend has been refactored for better maintainability:
- **Modular Architecture**: Separated concerns into focused modules
- **Proper Logging**: Replaced print statements with structured logging via `app_logger`
- **Centralized Configuration**: Environment variables managed in `config/settings.py`
- **Consistent Error Handling**: Standardized error responses across all endpoints
- **Reduced Code Duplication**: Common API configuration logic extracted to reusable functions
- **Clean Separation**: Business logic moved to service layer, keeping controllers thin

## Development Notes

- The application runs on port 8080 via nginx proxy
- Frontend uses session state management for multi-page workflows
- Backend uses Pydantic for request/response validation and structured output
- vLLM services require GPU resources with NVIDIA drivers
- All services communicate through a shared Docker network
- Backend follows a layered architecture pattern with clear separation of concerns