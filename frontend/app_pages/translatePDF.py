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

    # Display PDF info and time estimation
    def get_pdf_info_and_estimate(pdf_file):
        """Get page count and estimate processing time"""
        try:
            pdf_bytes = io.BytesIO(pdf_file.getvalue())
            doc = fitz.open("pdf", pdf_bytes)
            page_count = len(doc)
            doc.close()

            # Time estimation based on empirical data: 333 pages = 75 minutes
            # That's approximately 13.5 seconds per page
            seconds_per_page = 13.5
            estimated_seconds = page_count * seconds_per_page

            # Convert to human readable format
            if estimated_seconds < 60:
                time_str = f"{int(estimated_seconds)} seconds"
            elif estimated_seconds < 3600:
                minutes = int(estimated_seconds / 60)
                time_str = f"{minutes} minutes"
            else:
                hours = int(estimated_seconds / 3600)
                minutes = int((estimated_seconds % 3600) / 60)
                if minutes > 0:
                    time_str = f"{hours}h {minutes}m"
                else:
                    time_str = f"{hours} hours"

            return page_count, time_str, estimated_seconds
        except Exception:
            return None, None, None

    # Show PDF information and time estimate
    if st.session_state.pdf:
        page_count, estimated_time, estimated_seconds = get_pdf_info_and_estimate(st.session_state.pdf)

        if page_count:
            st.subheader("📄 Document Information")
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Pages", page_count)

            with col2:
                st.metric("Estimated Time", estimated_time)

            # Show warning for long documents
            if estimated_seconds > 1800:  # 30 minutes
                st.warning(f"⏰ Large document detected! This translation may take approximately **{estimated_time}**. Please be patient and don't close the browser.")
            elif estimated_seconds > 300:  # 5 minutes
                st.info(f"⏱️ This translation is estimated to take **{estimated_time}**. You can continue using other tabs while processing.")
            else:
                st.success(f"✅ Quick processing expected: approximately **{estimated_time}**")

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
                'url': st.session_state.openaiapiurl,
                'authorization': st.session_state.openapitoken,
                'translation_model_name': st.session_state.get('selected_model', 'default')
            }

            # Send the request to the backend
            response = requests.post(backend_url, files=files, data=data, timeout=14400)  # 4 hour timeout

            # Handle the response
            if response.status_code == 200:
                pdf_bytes = io.BytesIO(response.content)
                return pdf_bytes
            else:
                st.error(f"Error: {response.text}")
                return None
        except requests.exceptions.Timeout:
            st.error("Request timed out. The document may be too large or complex.")
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

            # Get time estimate for spinner message
            page_count, estimated_time, estimated_seconds = get_pdf_info_and_estimate(st.session_state.pdf)

            if estimated_time:
                spinner_message = f"🔄 Translating {page_count} pages... Estimated time: {estimated_time}"
            else:
                spinner_message = "🔄 Translating PDF... This may take several minutes for large documents."

            # Show spinner with additional timer for long documents
            if estimated_seconds and estimated_seconds > 300:  # 5+ minutes
                # Create containers for progress info
                progress_container = st.container()
                with progress_container:
                    timer_placeholder = st.empty()
                    progress_placeholder = st.empty()

                import threading
                import time

                # Timer variables
                start_time = time.time()
                translation_complete = threading.Event()

                def update_timer():
                    """Update timer display while processing"""
                    while not translation_complete.is_set():
                        elapsed = time.time() - start_time
                        elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"

                        if estimated_seconds:
                            progress_pct = min((elapsed / estimated_seconds) * 100, 99)
                            timer_placeholder.write(f"⏱️ Elapsed: {elapsed_str} | Estimated: {estimated_time} | Progress: ~{progress_pct:.0f}%")
                        else:
                            timer_placeholder.write(f"⏱️ Elapsed: {elapsed_str}")

                        time.sleep(1)

                # Start timer thread
                timer_thread = threading.Thread(target=update_timer)
                timer_thread.daemon = True
                timer_thread.start()

                # Show spinner while processing
                with st.spinner(spinner_message):
                    translated_pdf = translate_pdf(file_path, input_language, output_language, include_tbl_content)

                # Stop timer
                translation_complete.set()
                timer_placeholder.empty()
                progress_placeholder.empty()
            else:
                # Simple spinner for quick translations
                with st.spinner(spinner_message):
                    translated_pdf = translate_pdf(file_path, input_language, output_language, include_tbl_content)

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