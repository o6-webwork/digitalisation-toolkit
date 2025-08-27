import streamlit as st
import os 
import requests
from dotenv import load_dotenv
import json
# Load environment variables from .env file
load_dotenv()
API_URL = os.getenv("API_URL")
API_PORT = os.getenv("API_PORT")
#st.set_page_config(layout="wide")
models = [
    #"facebook/opt-125m",
    #"facebook/opt-350m",
    "Qwen/Qwen2.5-7B-Instruct",
    #"Qwen/Qwen2.5-1.5B-Instruct",
    #"microsoft/Phi-3-mini-4k-instruct",
    #"SeaLLMs/SeaLLMs-v3-1.5B-Chat"
]

#selected_model = st.selectbox("Choose a model for inference:", models,index=4)
#Prompt Config Loading
# if 'prompt_value' not in st.session_state or 'headerlist' not in st.session_state:
if 'request' not in st.session_state or 'required_schema' not in st.session_state:
    st.warning("Prompt configuration has not been set. Please configure your prompt on the previous page or load a configuration file.")
    #st.stop()

def load_config(uploaded_file):
    try:
        config = json.load(uploaded_file)
        # st.session_state.prompt_value = config.get('prompt_value', '')
        # st.session_state.headerlist = config.get('headerlist', [])
        st.session_state.request = config.get('request', '')
        st.session_state.required_schema = config.get('required_schema', [])
        st.success('Configuration loaded successfully.')
    except Exception as e:
        st.error(f'Failed to load configuration: {e}')

# Function to load configuration from uploaded file
def load_config(uploaded_file):
    try:
        config = json.load(uploaded_file)
        # st.session_state.prompt_value = config.get('prompt_value', '')
        # st.session_state.headerlist = config.get('headerlist', [])
        st.session_state.request = config.get('request', '')
        st.session_state.required_schema = config.get('required_schema', [])
        st.success('Configuration loaded successfully.')
    except Exception as e:
        st.error(f'Failed to load configuration: {e}')


uploaded_config = st.file_uploader('Upload a configuration file', type="json.structured.config")
if uploaded_config is not None:
    load_config(uploaded_config)
    #st.rerun(scope = "fragment")

payload = {
    # "request": st.session_state.get('prompt_value', ''),
    # "required_schema": st.session_state.get('headerlist', [])
    "request": st.session_state.get('request', ''),
    "required_schema": st.session_state.get('required_schema', [])
}
st.write("Current Prompt:", payload)

# if 'prompt_value' in st.session_state:
if 'request' in st.session_state:
# Input for configuration name
    config_name = st.text_input('Enter a name for the configuration (used for the filename):', '')


    if st.button('Save Configuration'):
        if config_name.strip() == '':
            st.error('Please enter a configuration name to save.')
        else:
            config_json = json.dumps(payload, indent=4)
            config_filename = f"{config_name.strip().replace(' ', '_')}.json.structured.config"
            st.download_button(
                label="Download Configuration",
                data=config_json,
                file_name=config_filename,
                mime="application/json"
            )
# --- End of added functionality ---

input_text = st.text_area("Input text for the model to process:", "")

# backend_url = "http://localhost:8000//structured-inference"
backend_url = os.getenv("BACKEND_STRUCTURED_INF_URL")

def structured_inference(openaiapi, input_text, prompt_value, headerlist):
    """
    Sends the df to the FastAPI backend and returns structured inference.
    """
    try:
        # Prepare the files and parameters for the request
        data = {
            'openaiapi': openaiapi,
            'input_text': input_text,
            'prompt_value': prompt_value,
            'headerlist': headerlist,
            'url': st.session_state.openaiapiurl,
            'authorization':st.session_state.openapitoken,
            'modelname':st.session_state['selected_model']
        }

        print(data)

        # Send the request to the backend
        response = requests.post(backend_url, json=data)

        # Handle the response
        if response.status_code == 200:
            return response.json()  # The generated schema
        else:
            st.error(f"Error: {response.text}")
            return None
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

if st.button("Run Inference"):
    if input_text.strip() == "":
        st.warning("Please provide input text for inference.")
    # elif 'headerlist' not in st.session_state:
    elif 'required_schema' not in st.session_state:
        st.warning("Please provide a schema for inference.")
    else:
        # ans = structured_inference(st.session_state.openaiapi, str(input_text), st.session_state.prompt_value, st.session_state.headerlist)
        ans = structured_inference(st.session_state.openaiapi, str(input_text), st.session_state.request, st.session_state.required_schema)
        st.write(f"Output: {ans}")