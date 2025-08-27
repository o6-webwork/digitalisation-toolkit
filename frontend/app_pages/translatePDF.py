import streamlit as st
import requests
import tempfile
from dotenv import load_dotenv
import os
import io
import fitz

try:
    cache_function = st.cache_data  # For Streamlit 1.18 and above
except AttributeError:
    cache_function = st.experimental_memo  # For older versions

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
    input_language = st.selectbox("Select Input Language (optional)", options=[""] + [code for code in LANGCODES])
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

    # Define a progress bar for showing the translation progress
    progress_bar = st.progress(0)

    load_dotenv()
    # FastAPI backend URL
    # backend_url = "http://localhost:8000/translate-pdf"
    backend_url = os.getenv("BACKEND_URL")

    def translate_pdf(file_path, input_lang, output_lang, include_tbl_content):
        """
        Sends the PDF to the FastAPI backend and returns the translated file.
        """
        try:
            # Prepare the files and parameters for the request
            files = {'file': open(file_path, 'rb')}
            data = {
                'input_language': input_lang,
                'output_language': output_lang,
                'include_tbl_content': include_tbl_content,
                'url': st.session_state.openaiapiurl + "/v1/chat/completions",
                'authorization':st.session_state.openapitoken,
                'translation_model_name':st.session_state['selected_model']
            }

            print(data)

            # Send the request to the backend
            response = requests.post(backend_url, files=files, data=data)

            # Handle the response
            if response.status_code == 200:
                print("✅ Received translated PDF from backend")
                pdf_bytes = io.BytesIO(response.content)

                return pdf_bytes
            else:
                st.error(f"Error: {response.text}")
                return None
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

            wait_message = st.empty()
            
            wait_message.write("Translating the document... Please wait.")
            
            translated_pdf = translate_pdf(file_path, input_language, output_language, include_tbl_content)
            if translated_pdf:
                try:
                    pdf_check = io.BytesIO(translated_pdf.getvalue())
                    doc = fitz.open("pdf", pdf_check)

                    if len(doc) > 0:
                        wait_message.empty()
                        st.download_button("Download Translated PDF", translated_pdf.getvalue(), file_name="translated.pdf", mime="application/pdf")
                    else:
                        wait_message.empty()
                        st.error("Translation completed, but the document is empty.")
                except Exception as e:
                    wait_message.empty()
                    st.error(f"Error checking translated PDF: {e}")
            else:
                wait_message.empty()
                st.error("Failed to translate the document.")
        else:
            st.error("Please upload a PDF file.")