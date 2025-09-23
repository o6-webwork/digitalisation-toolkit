import mimetypes
import tempfile
import io
from fastapi import FastAPI, File, UploadFile, Form, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# Local imports
from config.settings import settings
from models.schemas import TranslationRequest, HeaderItem
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

# Allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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
    except Exception as e:
        app_logger.error(f"Translation endpoint error: {str(e)}")
        return {"error": str(e)}

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

    except Exception as e:
        app_logger.error(f"PDF translation endpoint error: {str(e)}")
        return {"error": str(e)}


@app.post("/free-processing")
async def free_processing(
    text: str = Form(...),
    system_prompt: str = Form(...),
    user_prompt: str = Form(...),
    url: str = Form(...),
    authorization: str = Form(...),  
    model_name: str = Form(...)
):  
    try:
        app_logger.info("Received free processing request")
        
        # Get API configuration
        final_url, final_auth, final_model = settings.get_api_config(
            url, authorization, model_name
        )
        
        result = await llm_service.free_processing(
            text,
            system_prompt,
            user_prompt,
            final_url,
            final_auth,
            final_model
        )
        
        return result
        
    except Exception as e:
        app_logger.error(f"Free processing endpoint error: {str(e)}")
        return f"Error: {str(e)}"

@app.post("/prompt-page")
async def prompt_page(
    openaiapi: bool = Form(...),
    schema_prompt_value: str = Form(...),
    prompt_form_submitted: bool = Form(...),
    url: str = Form(...),
    authorization: str = Form(...),  
    model_name: str = Form(...)
):  
    try:
        app_logger.info("Received schema generation request")
        
        # Get API configuration
        final_url, final_auth, final_model = settings.get_api_config(
            url, authorization, model_name
        )
        
        result = await llm_service.generate_schema(
            schema_prompt_value,
            final_url,
            final_auth,
            final_model
        )
        
        return result
        
    except Exception as e:
        app_logger.error(f"Schema generation endpoint error: {str(e)}")
        return {"error": str(e)}
      


@app.post("/structured-inference")
async def structured_inference(
    openaiapi: bool = Body(...),
    input_text: str = Body(...),
    prompt_value: str = Body(...),
    headerlist: List[HeaderItem] = Body(...),
    url: str = Body(...),
    authorization: str = Body(...),  
    modelname: str = Body(...)
):  
    try:
        app_logger.info("Received structured inference request")
        
        # Get API configuration
        final_url, final_auth, final_model = settings.get_api_config(
            url, authorization, modelname
        )
        
        result = await llm_service.structured_inference(
            input_text,
            prompt_value,
            headerlist,
            final_url,
            final_auth,
            final_model
        )
        
        return result
        
    except Exception as e:
        app_logger.error(f"Structured inference endpoint error: {str(e)}")
        return f"Error: {str(e)}"
