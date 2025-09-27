import mimetypes
import tempfile
import io
import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# Local imports
from config.settings import settings
from models.schemas import TranslationRequest, PromptPageRequest, StructuredInferenceRequest, FreeProcessingRequest
from services.translation_service import TranslationService
from services.document_service import DocumentService
from services.llm_service import LLMService
from utils.logger import app_logger

# Initialize services
translation_service = TranslationService()
document_service = DocumentService()
llm_service = LLMService()

# Initialize FastAPI app
app = FastAPI(title="Digitalisation Toolkit API", version="1.0.0")

# Allow cross-origin requests from specific origins only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    app_logger.info("Digitalisation Toolkit API starting up")

@app.on_event("shutdown")
async def shutdown_event():
    app_logger.info("Digitalisation Toolkit API shutting down")


@app.post("/translate")
async def translate(request: TranslationRequest):
    """
    Endpoint for translating text from input_language to output_language.
    """
    try:
        app_logger.info("Received translation request")
        url, authorization, model_name = settings.get_api_config(
            request.url, request.authorization, request.translation_model_name
        )

        translated_text = await translation_service.translate_text(
            request.text,
            request.input_language,
            request.output_language,
            url,
            authorization,
            model_name
        )
        return {"translated_text": translated_text}
    except ValueError as e:
        app_logger.error(f"Translation validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        app_logger.error(f"Translation endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/translate-pdf")
async def translate_pdf(
    file: UploadFile = File(...),
    input_language: str = Form(...),
    output_language: str = Form(...),
    include_tbl_content: bool = Form(...),
    url: str = Form(...),
    authorization: str = Form(...),  
    translation_model_name: str = Form(...)
):
    """
    API endpoint to handle PDF translation
    """
    try:
        app_logger.info("Received PDF translation request")
        
        # Validate the file extension and MIME type
        file_extension = file.filename.split('.')[-1].lower()
        mime_type, _ = mimetypes.guess_type(file.filename)

        if file_extension != 'pdf' or mime_type != 'application/pdf':
            raise ValueError("The uploaded file is not a PDF.")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        try:
            # Get API configuration
            final_url, final_auth, final_model = settings.get_api_config(
                url, authorization, translation_model_name
            )

            # Translate PDF using document service
            translated_pdf_bytes = await document_service.translate_pdf(
                temp_file_path,
                input_language,
                output_language,
                include_tbl_content,
                final_url,
                final_auth,
                final_model
            )

            app_logger.info("Successfully generated translated PDF")
            return StreamingResponse(
                io.BytesIO(translated_pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=translated.pdf"}
            )
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                app_logger.info(f"Cleaned up temporary file: {temp_file_path}")

    except ValueError as e:
        app_logger.error(f"PDF translation validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        app_logger.error(f"PDF translation endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/free-processing")
async def free_processing(request: FreeProcessingRequest):  
    try:
        app_logger.info("Received free processing request")
        
        # Get API configuration
        final_url, final_auth, final_model = settings.get_api_config(
            request.url, request.authorization, request.model_name
        )

        result = await llm_service.free_processing(
            request.text,
            request.system_prompt,
            request.user_prompt,
            final_url,
            final_auth,
            final_model
        )
        
        return result
        
    except ValueError as e:
        app_logger.error(f"Free processing validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        app_logger.error(f"Free processing endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/prompt-page")
async def prompt_page(request: PromptPageRequest):  
    try:
        app_logger.info("Received schema generation request")
        
        # Get API configuration
        final_url, final_auth, final_model = settings.get_api_config(
            request.url, request.authorization, request.model_name
        )

        result = await llm_service.generate_schema(
            request.schema_prompt_value,
            final_url,
            final_auth,
            final_model
        )
        
        return result
        
    except ValueError as e:
        app_logger.error(f"Schema generation validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        app_logger.error(f"Schema generation endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
      


@app.post("/structured-inference")
async def structured_inference(request: StructuredInferenceRequest):  
    try:
        app_logger.info("Received structured inference request")
        
        # Get API configuration
        final_url, final_auth, final_model = settings.get_api_config(
            request.url, request.authorization, request.modelname
        )

        result = await llm_service.structured_inference(
            request.input_text,
            request.prompt_value,
            request.headerlist,
            final_url,
            final_auth,
            final_model
        )
        
        return result
        
    except ValueError as e:
        app_logger.error(f"Structured inference validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        app_logger.error(f"Structured inference endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

