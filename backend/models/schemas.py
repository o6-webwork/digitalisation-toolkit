from pydantic import BaseModel, conlist
from typing import List, Union
from enum import Enum

class TranslationRequest(BaseModel):
    text: Union[str, List[str]]
    input_language: str
    output_language: str
    user_prompt: str
    url: str
    authorization: str
    translation_model_name: str

class ColumnType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"

class ColumnInfo(BaseModel):
    column_name: str
    column_type: ColumnType
    reasoning: str
    example: str

class ColumnInfoList(BaseModel):
    columns: conlist(ColumnInfo, min_length=1)

class HeaderItem(BaseModel):
    column_name: str
    column_type: str

class PromptPageRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    openaiapi: bool
    schema_prompt_value: str
    prompt_form_submitted: bool
    url: str
    authorization: str
    model_name: str

class StructuredInferenceRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    openaiapi: bool
    input_text: str
    prompt_value: str
    headerlist: List[HeaderItem]
    url: str
    authorization: str
    modelname: str

class FreeProcessingRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    text: str
    system_prompt: str
    user_prompt: str
    url: str
    authorization: str
    model_name: str