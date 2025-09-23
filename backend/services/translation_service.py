import asyncio
from typing import Union, List
from utils.api_client import APIClient
from utils.logger import app_logger

class TranslationService:
    """Service for handling text translation"""

    @staticmethod
    async def translate_text(
        text: Union[str, List[str]],
        input_lang: str,
        output_lang: str,
        url: str,
        authorization: str,
        model_name: str
    ) -> str:
        """Translate text using external model API"""
        try:
            app_logger.info(f"Translating from {input_lang} to {output_lang}")
            app_logger.debug(f"Using model: {model_name}, URL: {url}")

            async with APIClient(url, authorization) as client:
                translation_request = {
                    "model": model_name,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Translate the following {input_lang} text '{text}' into {output_lang} directly, without altering the original meaning. Keep all numbers, math equations, symbols, unicode, and formatting (e.g., blank lines, dashes) intact. Do not add interpretations, summaries, or personal perspectives. The translation should be natural, accurate, clean, and faithful to the original text."
                        }
                    ]
                }

                response_data = await client.post("/v1/chat/completions", translation_request)
                content = response_data["choices"][0]["message"]["content"]
                app_logger.info("Translation completed successfully")
                return content

        except Exception as e:
            error_msg = f"Translation error: {str(e)}"
            app_logger.error(error_msg)
            return error_msg

    @staticmethod
    async def translate_batch(
        texts: List[str],
        input_lang: str,
        output_lang: str,
        url: str,
        authorization: str,
        model_name: str,
        batch_size: int = 5
    ) -> List[str]:
        """Translate multiple texts concurrently in batches"""
        try:
            app_logger.info(f"Batch translating {len(texts)} texts from {input_lang} to {output_lang}")

            async with APIClient(url, authorization) as client:
                results = []

                # Process texts in batches to avoid overwhelming the API
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    app_logger.info(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")

                    # Create translation requests for this batch
                    requests = []
                    for text in batch:
                        translation_request = {
                            "model": model_name,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": f"Translate the following {input_lang} text '{text}' into {output_lang} directly, without altering the original meaning. Keep all numbers, math equations, symbols, unicode, and formatting (e.g., blank lines, dashes) intact. Do not add interpretations, summaries, or personal perspectives. The translation should be natural, accurate, clean, and faithful to the original text."
                                }
                            ]
                        }
                        requests.append(translation_request)

                    # Execute batch requests concurrently
                    batch_responses = await client.post_batch("/v1/chat/completions", requests)

                    # Extract content from responses
                    batch_results = []
                    for response_data in batch_responses:
                        try:
                            content = response_data["choices"][0]["message"]["content"]
                            batch_results.append(content)
                        except (KeyError, IndexError) as e:
                            app_logger.error(f"Error parsing response: {e}")
                            batch_results.append(f"Translation error: {str(e)}")

                    results.extend(batch_results)

                app_logger.info(f"Batch translation completed successfully for {len(results)} texts")
                return results

        except Exception as e:
            error_msg = f"Batch translation error: {str(e)}"
            app_logger.error(error_msg)
            return [error_msg] * len(texts)