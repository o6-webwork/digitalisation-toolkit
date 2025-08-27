import os
from fastapi import FastAPI, File, UploadFile, Form, Body
import mimetypes
from fastapi.responses import StreamingResponse
import tempfile
import json
import requests
import pymupdf, fitz
from pypdf import PdfReader, PdfWriter
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions,EasyOcrOptions
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel, conlist
from enum import Enum
from openai import OpenAI
from pydantic import create_model
from typing import List
import io
from typing import List, Union

load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins or set your frontend URL here
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

######################################################
######################################################

# Translate Page

class TranslationRequest(BaseModel):
    # text: str
    text: Union[str, List[str]]
    input_language: str
    output_language: str
    user_prompt: str
    url: str
    authorization: str
    translation_model_name: str

def translatepdf_with_model(text, input_lang, output_lang, url, authorization,translation_model_name):
    """
    Translate text using an external model (such as OpenAI or other translation models).
    """
    try:
        print (text)
        print (input_lang)
        print (output_lang)
        print (url)
        print (authorization)
        print (translation_model_name)
        # Use environment variables if url or authorization are not provided
        if not url:
            url = os.getenv("TRANSLATION_API_URL")
        if not authorization:
            authorization = os.getenv("TRANSLATION_API_TOKEN", "token-abc123")  # Default token
        if not translation_model_name:
            translation_model_name = os.getenv("TRANSLATION_MODEL", "sealion")  # Default model

        if not authorization or not url:
            return "Error: API URL or token is not configured."
        
        headers = {
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {authorization}"
        }

        translation_request = {
            "model": translation_model_name,
            "messages": [
                {
                "role": "user", 
                "content": f"Translate the following {input_lang} text '{text}' into {output_lang} directly, without altering the original meaning. Keep all numbers, math equations, symbols, unicode, and formatting (e.g., blank lines, dashes) intact. Do not add interpretations, summaries, or personal perspectives. The translation should be natural, accurate, clean, and faithful to the original text."
                }
            ]
        }

        response = requests.post(url, headers=headers, json=translation_request, timeout=600)
        if response.status_code == 200:
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"]
            print (content)
            return content
        else:
            return f"Error: Request failed with status code {response.status_code}"
    except requests.exceptions.Timeout:
        print ("In request error")
        return "Error: Request timed out"
    except requests.exceptions.RequestException as e:
        print ("in network error")
        return f"Network error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@app.post("/translate")
async def translate(request: TranslationRequest):
    print (TranslationRequest)
    """
    Endpoint for translating text from input_language to output_language.
    """
    translated_text = translatepdf_with_model(
        request.text, 
        request.input_language, 
        request.output_language,
        request.url,
        request.authorization,
        request.translation_model_name

    )
    return {"translated_text": translated_text}

######################################################
######################################################

# Translate PDF

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
        print (input_language)
        print (output_language)
        print (file)
        print(url) 
        print(authorization) 
        print (translation_model_name)
        # Validate the file extension and MIME type
        file_extension = file.filename.split('.')[-1].lower()
        mime_type, _ = mimetypes.guess_type(file.filename)

        if file_extension != 'pdf' or mime_type != 'application/pdf':
            raise Exception(status_code=400, detail="The uploaded file is not a PDF.")
        
        # print (file)
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            # Write the content of the uploaded PDF to the temp file
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        # Continue processing as before
        translated_pdf_path  = document_translator(temp_file_path, input_language, output_language, include_tbl_content, url, authorization, translation_model_name)
        print("✅ Successfully generated translated PDF")
        return StreamingResponse(
            io.BytesIO(translated_pdf_path), 
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=translated.pdf"}
        )


    except Exception as e:
        print(f"❌ Exception in translate_pdf: {e}")
        return {"error": str(e)}


def document_translator(file_path, input_lang, output_lang, include_tbl, url, authorization, translation_model_name):
    """
    Translate text and tables from the uploaded PDF and return a translated version.
    """
    try:
        reader = PdfReader(file_path)
        if len(reader.pages) == 0:
            raise ValueError("The PDF document is empty.")
    except Exception as e:
        raise Exception(f"Error: The PDF file is corrupted or invalid. {str(e)}")

    print("bfr redoc")
    redoc = docling_dict_convert(file_path)
    print("after redoc")
    doc_info = redoc["Pages"]
    print("hi")

    output_path = "/tmp/translated.pdf"

    with fitz.open(file_path) as doc:
        ocg_xref = doc.add_ocg(f"{output_lang} Translation", on=True)
        WHITE = pymupdf.pdfcolor["white"]
        textflags = pymupdf.TEXT_DEHYPHENATE

        for page in doc:
            page_no = page.number + 1

            for text_info in doc_info[str(page_no)]["Texts"]:
                try:
                    text_bbox = text_info["bbox"]
                    text_text = text_info["text"]
                    text_text_translated = translatepdf_with_model(text_text, input_lang, output_lang, url, authorization, translation_model_name)
                    text_rect = fitz.Rect(reformat_bbox(text_bbox))
                    page.add_redact_annot(text_rect, text="")
                    page.apply_redactions()
                    page.insert_htmlbox(
                        text_rect,
                        f"<div style='font-family: sans-serif;'>{text_text_translated}</div>",
                        oc=ocg_xref
                    )
                except KeyError as e:
                    print(str(e))
                    continue

            if include_tbl:
                for table_info in doc_info[str(page_no)]["Tables"]:
                    for cell in table_info["table_cells"]:
                        table_bbox = cell["bbox"]
                        table_text = cell["text"]
                        table_text_translated = translatepdf_with_model(table_text, input_lang, output_lang, url, authorization, translation_model_name)
                        if table_text_translated:
                            table_rect = fitz.Rect(reformat_bbox(table_bbox))
                            page.add_redact_annot(table_rect, text="")
                            page.apply_redactions()
                            page.insert_htmlbox(
                                table_rect,
                                f"<div style='font-family: sans-serif;'>{table_text_translated}</div>",
                                oc=ocg_xref
                            )

            page.clean_contents()

        doc.subset_fonts()
        doc.ez_save(output_path, clean=True, deflate=True, garbage=4)
        # Optionally add: progress_bar.progress(83)

    # Now compress using PdfWriter
    writer = PdfWriter(clone_from=output_path)
    for page in writer.pages:
        for img in page.images:
            img.replace(img.image, quality=80)  # Lower quality to reduce size

    with open(output_path, "wb") as f:
        writer.write(f)

    # Read final optimized PDF into memory and return as bytes
    with open(output_path, "rb") as f:
        pdf_bytes = f.read()

    return pdf_bytes

def docling_dict_convert(file_path):
    """
    Convert the uploaded PDF to a structured JSON format using Docling.
    """
    print ("before pipeline")
    print(f"ARTIFACTS_PATH: {os.getenv('ARTIFACTS_PATH')}")
    ocr_options = EasyOcrOptions(
    # lang=["en","ch_sim","ch_tra","ar","ms","id"],  # Specify languages as needed
    lang=["en"],  # Specify languages as needed
    model_storage_directory=os.getenv('MODEL_STORAGE_DIRECTORY'),  # Make sure this is a local path
    download_enabled=False,  # Disable downloading of models
        )
    pipeline_options = PdfPipelineOptions(artifacts_path=os.getenv("ARTIFACTS_PATH"),enable_remote_services=False, ocr_options=ocr_options)
    print ("in pipeline")
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )
    print ("after converter")
    try: 
        result = converter.convert(file_path).document
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return f"Error: {str(e)}"
    print ("after result")
    doc = result.export_to_dict()

    print ("after doc")

    redoc = {"Pages": {}}
    for page_no, page_dim in doc["pages"].items():
        redoc["Pages"].update(
            {page_no: {"Texts": [], "Tables": [], "Page_Size": page_dim["size"]}}
        )

    for text_data in doc["texts"]:
        prov = text_data.get("prov", [{}])[0]
        text_label = text_data["label"]
        text_text = text_data["text"]
        text_page_no = prov["page_no"]
        text_bbox = prov["bbox"]
        text_bbox["t"] = redoc["Pages"][str(text_page_no)]["Page_Size"]["height"] - text_bbox["t"]
        text_bbox["b"] = redoc["Pages"][str(text_page_no)]["Page_Size"]["height"] - text_bbox["b"]
        redoc["Pages"][str(text_page_no)]["Texts"].append({
            "label": text_label,
            "text": text_text,
            "bbox": text_bbox,
        })
    print ("after for loop")

    # Add table data
    if doc["tables"]:
        # print ("in table")
        for table_data in doc["tables"]:
            prov = table_data.get("prov", [{}])[0]
            table_page_no = prov["page_no"]
            table_bbox = prov["bbox"]
            table_bbox["t"] = redoc["Pages"][str(table_page_no)]["Page_Size"]["height"] - table_bbox["t"]
            table_bbox["b"] = redoc["Pages"][str(table_page_no)]["Page_Size"]["height"] - table_bbox["b"]
            table_cell_list = []
            # print ("bfr for loop")
            for table_cell in table_data["data"]["table_cells"]:
                try:
                    # Check if 'bbox' exists before accessing it
                    if "bbox" not in table_cell:
                        print(f"Warning: Missing 'bbox' for table cell: {table_cell}")
                        continue  # Skip this table cell
                    
                    table_cell["bbox"]["t"] = redoc["Pages"][str(table_page_no)]["Page_Size"]["height"] - table_cell["bbox"]["t"]
                    table_cell["bbox"]["b"] = redoc["Pages"][str(table_page_no)]["Page_Size"]["height"] - table_cell["bbox"]["b"]
                    table_cell_list.append({"text": table_cell["text"], "bbox": table_cell["bbox"]})
                    # print("in for loop")
                except Exception as e:
                    print(f"Exception in table cell processing: {str(e)}")

            print ("test")
            redoc["Pages"][str(table_page_no)]["Tables"].append({
                "table_cells": table_cell_list,
                "bbox": table_bbox
            })
    return redoc

def reformat_bbox(docling_bbox):
    """
    Reformat bounding box coordinates from Docling format.
    """
    return docling_bbox.get('l'), docling_bbox.get('t'), docling_bbox.get('r'), docling_bbox.get('b')

######################################################
######################################################

# Free Processing

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
        # Use environment variables if url or authorization are not provided
        if not url:
            url = os.getenv("LLM_API_URL", "http://localhost:11437/v1/chat/completions")  # Default URL
        if not authorization:
            authorization = os.getenv("TRANSLATION_API_TOKEN", "token-abc123")  # Default token
        if not model_name:
            model_name = os.getenv("LLM_MODEL", "qwen2.5")  # Default model

        if not authorization or not url:
            return "Error: API URL or token is not configured."
    except Exception as e:
        return f"Error: {str(e)}"

    headers = {"Content-Type": "application/json",
        "Authorization": f"Bearer {authorization}"}
    
    if not system_prompt:
        system_prompt = 'You are a helpful assistant.'
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": f"{user_prompt}: {text}"
        },
    ]
    
    data = {
        'model': model_name,
        'messages': messages,
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            # Parse the JSON response
            response_data = response.json()

            # Extract the result field
            content = response_data["choices"][0]["message"]["content"]

            # Return the content
            return content
        else:
            return f"Request failed with status code {response.status_code}"
    except Exception as e:
        return f"Error: {e}"  # Return an error message in case of failure

######################################################
######################################################

# Prompt Page

class ColumnType(str, Enum):
        STRING = "string"
        INTEGER = "integer"
        BOOLEAN = "boolean"

# Define column info
class ColumnInfo(BaseModel):
    column_name: str
    column_type: ColumnType
    reasoning: str
    example: str

# Define list of column info
class ColumnInfoList(BaseModel):
    columns: conlist(ColumnInfo,min_length=1) # type: ignore # ignore warning lol

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
        # Use environment variables if url or authorization are not provided
        if not url:
            url = os.getenv("LLM_API_URL", "http://localhost:11437/v1/chat/completions")  # Default URL
        if not authorization:
            authorization = os.getenv("TRANSLATION_API_TOKEN", "token-abc123")  # Default token
        if not model_name:
            model_name = os.getenv("LLM_MODEL", "qwen2.5")  # Default model

        if not authorization or not url:
            return "Error: API URL or token is not configured."
    except Exception as e:
        return f"Error: {str(e)}"
    
    # if openaiapi == True:       
        
    input_text = str(schema_prompt_value)
    system_prompt = 'You are a helpful assistant, Help the user come up with a valid json that suits the users needs'

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": str(input_text) #user input
        },
    ]
        
    # try:
    url = url + "/v1"
    client = OpenAI(base_url=url, api_key=authorization)
    completion = client.beta.chat.completions.parse(
        model=model_name,
        messages=messages,
        response_format=ColumnInfoList,
        extra_body=dict(guided_decoding_backend="outlines"),
    )
    if not completion or not hasattr(completion, 'choices') or not completion.choices:
        return {"error": "Error: No choices found in the API response"}
    
    message = completion.choices[0].message
    # print(message)
    if not message.parsed:
        return {"error": "Error: 'parsed' field is missing or empty in the response."}
    # print(message.parsed)
    # st.write(str(dict(message.parsed))) 
    # st.write(message.parsed.columns[0].model_dump_json())

    response_data = {
        "columns":[]
    }
    for atrribute in message.parsed.columns:
        response_data['columns'].append(atrribute.model_dump())
    
    return response_data
    # except Exception as e:
    #     return f"Error: {e}" # Return an error message in case of failure
      


######################################################
######################################################

# Structured Inference & Batch Structured Inference

def headers_to_json_schema(headers):
    """
    Convert a list of headers to a JSON schema string representing a list of objects.

    :param headers: List of dictionaries with 'column_name' and 'column_type'
    :return: JSON schema as a string
    """
    schema = {
        # "title": "Response",
        "type": "array",
        "items": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }

    for header in headers:
        column_name = header.column_name
        column_type = header.column_type

        schema["items"]["properties"][column_name] = {"type": column_type}
        schema["items"]["required"].append(column_name)

    return json.dumps(schema, indent=2)

def headers_to_pydantic(headers):
    """
    Convert a list of headers to a pydantic object

    :param headers: List of dictionaries with 'column_name' and 'column_type'
    :return: pydantic object
    """
    kwargs = {}
    for header in headers:
        column_name = header.column_name
        column_type = header.column_type
        if column_type == "string":
            column_type= str
        if column_type == "number":
            column_type= float
        if column_type == "boolean":
            column_type= bool
        kwargs[column_name] = (column_type,...)
        
    DynamicModel = create_model(
    'DynamicModel', **kwargs )
    
    return DynamicModel

class HeaderItem(BaseModel):
    column_name: str
    column_type: str
    
@app.post("/structured-inference")
async def structured_inference(
    openaiapi: bool = Body(...),
    input_text: str = Body(...),
    prompt_value: str = Body(...),
    headerlist: List[HeaderItem]  = Body(...),
    url: str = Body(...),
    authorization: str = Body(...),  
    modelname: str = Body(...)
):  
    try:
        # Use environment variables if url or authorization are not provided
        if not url:
            url = os.getenv("LLM_API_URL", "http://localhost:11437/v1/chat/completions")  # Default URL
        if not authorization:
            authorization = os.getenv("TRANSLATION_API_TOKEN", "token-abc123")  # Default token
        if not modelname:
            modelname = os.getenv("LLM_MODEL", "qwen2.5")  # Default model

        if not authorization or not url:
            return "Error: API URL or token is not configured."
    except Exception as e:
        return f"Error: {str(e)}"
        
    # if openaiapi == True:     
    if prompt_value is None:
        system_prompt = 'You are a helpful assistant.'
    else:
        system_prompt = prompt_value
        
    if input_text.strip() == "":
        return "Please provide input text for inference."
    else:
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": str(input_text) #user input
            },
        ]

        json_schema = json.loads(headers_to_json_schema(headerlist))
        
        data = {
            'model': modelname,
            'messages': messages,
            'response_format': {
                "type": "json_schema",
                "json_schema" : {
                    "name": "response",
                    "schema": json_schema
                }
            },
            'stream': False
        }
        
        try:
            url = url + "/v1"
            client = OpenAI(base_url=url, api_key=authorization)
            completion = client.beta.chat.completions.parse(
                model=modelname,
                messages=messages,
                response_format=headers_to_pydantic(headerlist),
                extra_body=dict(guided_decoding_backend="outlines"),
            )
            message = completion.choices[0].message
            # print(message)
            assert message.parsed
            # print(message.parsed)
            return str(dict(message.parsed))
        except Exception as e:
            return f"Error: {e}" # Return an error message in case of failure
