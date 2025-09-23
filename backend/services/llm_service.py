import json
from typing import List, Dict, Any
from openai import AsyncOpenAI
from pydantic import create_model
from utils.api_client import APIClient
from utils.logger import app_logger
from models.schemas import ColumnInfoList, HeaderItem

class LLMService:
    """Service for handling LLM interactions"""

    async def free_processing(
        self,
        text: str,
        system_prompt: str,
        user_prompt: str,
        url: str,
        authorization: str,
        model_name: str
    ) -> str:
        """Process text with custom prompts using LLM"""
        try:
            app_logger.info("Starting free text processing")

            async with APIClient(url, authorization) as client:
                if not system_prompt:
                    system_prompt = 'You are a helpful assistant.'

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{user_prompt}: {text}"}
                ]

                data = {
                    'model': model_name,
                    'messages': messages,
                }

                response_data = await client.post("", data)
                content = response_data["choices"][0]["message"]["content"]
                app_logger.info("Free processing completed successfully")
                return content

        except Exception as e:
            error_msg = f"Free processing error: {str(e)}"
            app_logger.error(error_msg)
            return error_msg

    async def generate_schema(
        self,
        schema_prompt: str,
        url: str,
        authorization: str,
        model_name: str
    ) -> Dict[str, Any]:
        """Generate schema using structured output"""
        try:
            app_logger.info("Generating schema with structured output")

            system_prompt = 'You are a helpful assistant, Help the user come up with a valid json that suits the users needs'

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(schema_prompt)}
            ]

            api_url = url + "/v1"
            client = AsyncOpenAI(base_url=api_url, api_key=authorization)
            completion = await client.beta.chat.completions.parse(
                model=model_name,
                messages=messages,
                response_format=ColumnInfoList,
                extra_body=dict(guided_decoding_backend="outlines"),
            )

            if not completion or not hasattr(completion, 'choices') or not completion.choices:
                return {"error": "Error: No choices found in the API response"}

            message = completion.choices[0].message
            if not message.parsed:
                return {"error": "Error: 'parsed' field is missing or empty in the response."}

            response_data = {"columns": []}
            for attribute in message.parsed.columns:
                response_data['columns'].append(attribute.model_dump())

            app_logger.info("Schema generation completed successfully")
            return response_data

        except Exception as e:
            error_msg = f"Schema generation error: {str(e)}"
            app_logger.error(error_msg)
            return {"error": error_msg}

    async def structured_inference(
        self,
        input_text: str,
        prompt_value: str,
        headers: List[HeaderItem],
        url: str,
        authorization: str,
        model_name: str
    ) -> str:
        """Perform structured inference with defined schema"""
        try:
            app_logger.info("Starting structured inference")

            if input_text.strip() == "":
                return "Please provide input text for inference."

            system_prompt = prompt_value if prompt_value else 'You are a helpful assistant.'

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(input_text)}
            ]

            api_url = url + "/v1"
            client = AsyncOpenAI(base_url=api_url, api_key=authorization)

            pydantic_model = self._headers_to_pydantic(headers)
            completion = await client.beta.chat.completions.parse(
                model=model_name,
                messages=messages,
                response_format=pydantic_model,
                extra_body=dict(guided_decoding_backend="outlines"),
            )

            message = completion.choices[0].message
            assert message.parsed

            app_logger.info("Structured inference completed successfully")
            return str(dict(message.parsed))

        except Exception as e:
            error_msg = f"Structured inference error: {str(e)}"
            app_logger.error(error_msg)
            return error_msg

    def _headers_to_json_schema(self, headers: List[HeaderItem]) -> str:
        """Convert headers to JSON schema"""
        schema = {
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

    def _headers_to_pydantic(self, headers: List[HeaderItem]):
        """Convert headers to Pydantic model"""
        kwargs = {}
        for header in headers:
            column_name = header.column_name
            column_type = header.column_type
            
            if column_type == "string":
                python_type = str
            elif column_type == "number":
                python_type = float
            elif column_type == "boolean":
                python_type = bool
            else:
                python_type = str
                
            kwargs[column_name] = (python_type, ...)
            
        return create_model('DynamicModel', **kwargs)