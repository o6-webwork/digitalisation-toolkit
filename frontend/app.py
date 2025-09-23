import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize session state variables
session_defaults = {
    'selected_page': "Data Loader",
    'previous_page': None,
    'data_loaded': False,
    'selected_columns': None,
    'selected_df': None,
    'prompt_form_submitted': False,
    'prompt_json_submitted': False,
    'translation_complete': False,
    'processing_complete': False,
    'url_edited': False,
    'last_fetched_url': None
}

st.set_page_config(layout='wide')

for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Define pages
dataloader = st.Page("app_pages/dataloaderPage.py", title="Data Loader")
translator = st.Page("app_pages/translatePage.py", title="Translate")
translator_pdf = st.Page("app_pages/translatePDF.py", title="Translate PDF")
free_processing = st.Page("app_pages/freeprocessingPage.py", title="Free Processing")
schema_builder = st.Page("app_pages/promptPage.py", title="Schema Builder")
structured_inference = st.Page("app_pages/structuredInferencePage.py", title="Structured Inference")
structured_batch_inference = st.Page("app_pages/structuredbatchInference.py", title="Structured Batch Inference")

data_pages = [dataloader]
processing_pages = [translator, translator_pdf, free_processing]
structured_pages = [schema_builder, structured_inference, structured_batch_inference]

page_dict = {
    "Data": data_pages,
    "Processing": processing_pages,
    "Structured Processing": structured_pages
}

@st.dialog("Error!")
def error_popup(e):
    st.write(f"{e}")
    refresh_button = st.button("Got it!")
    if refresh_button:
        st.rerun()

st.session_state.openaiapi = True
selected_page = st.navigation(page_dict)
translation_pages = [translator_pdf.title, translator.title]

translation_api_url = os.getenv("TRANSLATION_API_URL")
general_api_url = os.getenv("GENERAL_API_URL")
# Sidebar inputs
default_url = translation_api_url if selected_page.title in translation_pages else general_api_url
user_input_url = st.sidebar.text_input("API URL", value=default_url, key="openaiapiurl")
user_input_token = st.sidebar.text_input("API Token", value="token-abc123", key="openapitoken")

# Track if user edited URL
if user_input_url != default_url:
    st.session_state.url_edited = True

# Function to fetch models from API
def fetch_models(show_errors=False):
    url = user_input_url + "/v1/models"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_input_token}"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            model_list = [model["id"] for model in response.json()["data"]]
            st.session_state.model_list = model_list
            st.session_state.last_fetched_url = user_input_url
        elif response.status_code == 401:
            raise Exception(f"Response status {response.status_code} Unauthorized. Check your API token.")
        else:
            raise Exception(f"Response status {response.status_code}")

    except requests.exceptions.MissingSchema:
        if show_errors:
            error_popup(f"Missing Schema Error: Invalid URL '{user_input_url}'. No scheme supplied. Perhaps you meant 'http://{user_input_url}'?")
    
    except requests.exceptions.ConnectionError as conn_err:
        if show_errors:
            error_popup(f"Connection Error: Please check if the server is running and the URL is correct.\n\nDetails: {conn_err}")
    
    except requests.exceptions.HTTPError as http_err:
        if show_errors:
            status_code = http_err.response.status_code
            if status_code == 400:
                error_popup(f"Bad Request {status_code}: The server could not understand the request. Please check the URL and request format.\n\nDetails: {http_err}")
            elif status_code == 401:
                error_popup(f"Unauthorized {status_code}: Please check your API token.\n\nDetails: {http_err}")
            elif status_code == 403:
                error_popup(f"Forbidden {status_code}: You do not have permission to access the resource.\n\nDetails: {http_err}")
            elif status_code == 404:
                error_popup(f"Not Found {status_code}: The requested resource at {url} could not be found.\n\nPlease check if the URL is correct and if the API is running on the server (IP: {user_input_url}).")
            elif status_code == 500:
                error_popup(f"Internal Server Error {status_code}: There was an error on the server. Please try again later.\n\nDetails: {http_err}")
            else:
                error_popup(f"HTTP error occurred: {http_err} (Status Code: {status_code})")
    
    except requests.exceptions.RequestException as req_err:
        if show_errors:
            error_popup(f"Request Error: {req_err}\n\nPerhaps you meant 'http://{user_input_url}'?")
    
    except Exception as e:
        if show_errors:
            error_popup(f"Unexpected Error: The requested resource at {url} could not be found.\n\n"
                        f"Please check if the URL is correct and if the API is running on the server (IP: {user_input_url}).\n\nDetails: {e}")


# Automatically load models on first page load or URL change
if st.session_state.last_fetched_url != user_input_url:
    fetch_models(show_errors=st.session_state.url_edited)

# Manual refresh button
if st.sidebar.button("Refresh models"):
    fetch_models(show_errors=True)

# Model selection
if "model_list" in st.session_state:
    model_list = st.session_state.model_list
    selected_model = st.sidebar.selectbox("Choose model", model_list)
    st.session_state.selected_model = selected_model
else:
    st.session_state.pop("model_list", None)

# Run the selected page
selected_page.run()
