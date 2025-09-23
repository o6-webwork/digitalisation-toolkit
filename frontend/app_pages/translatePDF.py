import streamlit as st
import requests
import tempfile
from dotenv import load_dotenv
import os
import io
import fitz

# Use modern Streamlit caching
cache_function = st.cache_data

@st.dialog("Error!")
def error_popup(e):
    st.write(f"{e}")
    refresh_button = st.button("Got it!")
    if refresh_button:
        st.rerun()

LANGCODES = [
    ('English'), ('Malay (Bahasa Melayu)'), ('Indonesian (Bahasa Indonesia)'), ('Chinese'),
    ('Afrikaans'), ('Arabic'), ('Azerbaijani'), ('Belarusian'), ('Bulgarian'),
    ('Bengali'), ('Bosnian'), ('Catalan'), ('Czech'), ('Welsh'), ('Danish'),
    ('German'), ('Greek'), ('Esperanto'), ('Spanish'), ('Estonian'), ('Basque'),
    ('Persian'), ('Finnish'), ('Filipino'), ('French'), ('Irish'), ('Galician'),
    ('Gujarati'), ('Hebrew'), ('Hindi'), ('Croatian'), ('Haitian Creole'), ('Hungarian'),
    ('Armenian'), ('Icelandic'), ('Italian'), ('Japanese'), ('Georgian'), ('Kazakh'),
    ('Khmer'), ('Kannada'), ('Korean'), ('Kyrgyz'), ('Lao'), ('Lithuanian'),
    ('Latvian'), ('Macedonian'), ('Malayalam'), ('Mongolian'), ('Marathi'), ('Nepali'),
    ('Dutch'), ('Norwegian'), ('Punjabi'), ('Polish'), ('Portuguese'), ('Romanian'),
    ('Russian'), ('Slovak'), ('Slovenian'), ('Albanian'), ('Serbian'), ('Swedish'),
    ('Swahili'), ('Tamil'), ('Telugu'), ('Thai'), ('Turkish'), ('Ukrainian'),
    ('Urdu'), ('Vietnamese'), ('Yoruba'), ('Zulu')
]

# Set up the title and language selection
st.title("PDF Translation Page")

if 'pdf' not in st.session_state or st.session_state.pdf is None:
    st.warning("No data loaded. Please go to the Data Loader page and upload a pdf file.")
else:
# Language selection
    input_language = st.selectbox("Select Input Language (optional)", options=[""] + [code for code in LANGCODES], format_func=lambda x: "Automatic" if x == "" else x)
    output_language = st.selectbox("Select Output Language", options=[code for code in LANGCODES])

    # Save Options
    st.subheader("Save Options")
    if 'append_mode' in st.session_state:
        append_mode = st.session_state.append_mode
    else:
        append_mode = False

    # toggle for including table content
    include_tbl_content = st.toggle("Translate table contents")

    if append_mode:
        st.info("Processed output will be appended to the original file.")
    else:
        st.info("Processed output will be saved as a new file.")


    load_dotenv()
    # FastAPI backend URL
    # backend_url = "http://localhost:8000/translate-pdf"
    backend_url = os.getenv("BACKEND_URL")

    def translate_pdf_with_progress(file_path, input_lang, output_lang, include_tbl_content):
        """
        Sends the PDF to the FastAPI backend with progress updates.
        """
        try:
            # Prepare the files and parameters for the request
            files = {'file': open(file_path, 'rb')}
            data = {
                'input_language': input_lang,
                'output_language': output_lang,
                'include_tbl_content': include_tbl_content,
                'url': st.session_state.openaiapiurl,
                'authorization': st.session_state.openapitoken,
                'translation_model_name': st.session_state.get('selected_model', 'default')
            }

            # Use progress endpoint
            progress_url = backend_url.replace('/translate-pdf', '/translate-pdf-with-progress')

            # Create progress containers
            progress_container = st.container()

            with progress_container:
                status_text = st.empty()
                progress_bar = st.progress(0)
                details_text = st.empty()

            # Send request with streaming
            with requests.post(progress_url, files=files, data=data, stream=True,
                             headers={'Accept': 'text/event-stream'}) as response:

                if response.status_code != 200:
                    st.error(f"Error: {response.text}")
                    return None

                pdf_data = None

                # Process Server-Sent Events
                for line in response.iter_lines(decode_unicode=True):
                    if line.startswith('data: '):
                        try:
                            import json
                            event_data = json.loads(line[6:])  # Remove 'data: ' prefix

                            if event_data.get('type') == 'document_processing_start':
                                status_text.write("🔄 Starting document processing...")
                                progress_bar.progress(5)

                            elif event_data.get('type') == 'document_extraction':
                                status_text.write("📄 Extracting text from PDF...")
                                details_text.write(event_data.get('message', ''))
                                progress_bar.progress(15)

                            elif event_data.get('type') == 'document_extraction_complete':
                                status_text.write("✅ Text extraction completed")
                                progress_bar.progress(25)

                            elif event_data.get('type') == 'translation_start':
                                status_text.write("🔄 Starting translation...")
                                details_text.write(event_data.get('message', ''))
                                progress_bar.progress(30)

                            elif event_data.get('type') == 'translation_progress':
                                batch = event_data.get('batch', 0)
                                total_batches = event_data.get('total_batches', 1)
                                batch_progress = event_data.get('progress', 0)

                                status_text.write(f"🔄 Translating batch {batch}/{total_batches}...")
                                # Map translation progress from 30% to 80%
                                overall_progress = 30 + (batch_progress * 0.5)
                                progress_bar.progress(min(int(overall_progress), 80))

                            elif event_data.get('type') == 'translation_complete':
                                status_text.write("✅ Translation completed")
                                progress_bar.progress(80)

                            elif event_data.get('type') == 'pdf_generation_start':
                                status_text.write("📝 Generating translated PDF...")
                                progress_bar.progress(85)

                            elif event_data.get('type') == 'pdf_generation_progress':
                                page = event_data.get('page', 1)
                                total_pages = event_data.get('total_pages', 1)
                                status_text.write(f"📝 Processing page {page}/{total_pages}...")
                                # Map page progress from 85% to 95%
                                page_progress = 85 + ((page / total_pages) * 10)
                                progress_bar.progress(min(int(page_progress), 95))

                            elif event_data.get('type') == 'final_complete':
                                status_text.write("🎉 PDF translation completed!")
                                progress_bar.progress(100)
                                details_text.write("Ready for download")

                                # Extract PDF data
                                if 'pdf_data' in event_data:
                                    import base64
                                    pdf_bytes = base64.b64decode(event_data['pdf_data'])
                                    pdf_data = io.BytesIO(pdf_bytes)

                            elif event_data.get('type') == 'error':
                                status_text.error(f"❌ Error: {event_data.get('message')}")
                                return None

                        except json.JSONDecodeError:
                            continue  # Skip malformed JSON
                        except Exception as e:
                            st.error(f"Error processing progress: {e}")
                            continue

                return pdf_data

        except Exception as e:
            st.error(f"An error occurred: {e}")
            return None

    # If the "Start Translation" button is clicked
    if st.button('Start Translation'):
        if st.session_state.pdf:
            # Save the uploaded PDF to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(st.session_state.pdf.getvalue())
                file_path = temp_file.name

            # Use the progress-enabled translation
            translated_pdf = translate_pdf_with_progress(file_path, input_language, output_language, include_tbl_content)

            if translated_pdf:
                try:
                    pdf_check = io.BytesIO(translated_pdf.getvalue())
                    doc = fitz.open("pdf", pdf_check)

                    if len(doc) > 0:
                        st.success("🎉 Translation completed successfully!")
                        st.download_button(
                            "📥 Download Translated PDF",
                            translated_pdf.getvalue(),
                            file_name="translated.pdf",
                            mime="application/pdf"
                        )
                    else:
                        st.error("Translation completed, but the document is empty.")
                except Exception as e:
                    st.error(f"Error checking translated PDF: {e}")
            else:
                st.error("Failed to translate the document.")

            # Clean up temporary file
            try:
                import os
                os.unlink(file_path)
            except (OSError, FileNotFoundError):
                pass  # File already cleaned up or doesn't exist
        else:
            st.error("Please upload a PDF file.")