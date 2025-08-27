import streamlit as st
import os
import requests
import pandas as pd
import io
import json
from dotenv import load_dotenv
from st_aggrid import AgGrid, GridOptionsBuilder
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Load environment variables
load_dotenv()

# --- Utility Functions ---

def display_aggrid(df, title="DataFrame"):
    st.subheader(title)
    try:
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_default_column(wrapText=True, autoHeight=True)
        grid_options = gb.build()
        AgGrid(df, gridOptions=grid_options, enable_enterprise_modules=False, theme="streamlit", fit_columns_on_grid_load=True)
    except Exception:
        st.dataframe(df)

def download_processed_files(df, base_name):
    csv_buffer = df.to_csv(index=False).encode('utf-8')
    json_buffer = df.to_json(orient='records', indent=2).encode('utf-8')
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Processed_Data')

    st.download_button("Download as CSV", csv_buffer, file_name=f"{base_name}.csv", mime="text/csv")
    st.download_button("Download as JSON", json_buffer, file_name=f"{base_name}.json", mime="application/json")
    st.download_button("Download as Excel", excel_buffer.getvalue(), file_name=f"{base_name}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def is_prompt_config_ready():
    return 'request' in st.session_state and 'required_schema' in st.session_state

def run_inference(input_text, request, required_schema, openaiapiurl, openapitoken, selected_model):
    backend_url = os.getenv("BACKEND_STRUCTURED_INF_URL")
    data = {
        'openaiapi': True,
        'input_text': input_text,
        'prompt_value': request,
        'headerlist': required_schema,
        'url': openaiapiurl,
        'authorization': openapitoken,
        'modelname': selected_model
    }
    try:
        response = requests.post(backend_url, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Backend error: {response.text}")
            return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None

def load_config(uploaded_file):
    try:
        config = json.load(uploaded_file)
        st.session_state.request = config.get('request', '')
        st.session_state.required_schema = config.get('required_schema', [])
        st.success('Configuration loaded successfully.')
    except Exception as e:
        st.error(f'Failed to load configuration: {e}')

# --- Page Content ---

st.title("Structured Batch Inference")

if 'selected_df' not in st.session_state or st.session_state.selected_df is None:
    st.warning("No data loaded. Please go to the Data Loader page and upload a file.")
    st.stop()
else:
    df = st.session_state.selected_df

display_aggrid(df, title="Loaded DataFrame")

# Load config file
if not is_prompt_config_ready():
    st.warning("Prompt configuration has not been set. Please configure your prompt or load a configuration file.")

uploaded_config = st.file_uploader('Upload a configuration file', type='json.structured.config')
if uploaded_config:
    load_config(uploaded_config)

# Save Configuration
config_name = st.text_input('Enter a name for the configuration (used for the filename):', '')

if st.button('Save Configuration'):
    if config_name.strip() == '':
        st.error('Please enter a configuration name to save.')
    else:
        config = {
            'request': st.session_state.request,
            'required_schema': st.session_state.required_schema
        }
        config_json = json.dumps(config, indent=4)
        config_filename = f"{config_name.strip().replace(' ', '_')}.json.structured.config"
        st.download_button("Download Configuration", config_json, file_name=config_filename, mime="application/json")

st.subheader("Save Options")
append_mode = st.session_state.get("append_mode", False)

if append_mode:
    st.info("Processed output will be appended to the original file.")
else:
    st.info("Processed output will be saved as a new file.")

# --- Preview ---
if st.button("Preview"):
    st.subheader("Processing Preview")
    preview_df = df.sample(n=min(5, len(df)))
    request = st.session_state.get("request")
    required_schema = st.session_state.get("required_schema")
    openaiapiurl = st.session_state.get("openaiapiurl")
    openapitoken = st.session_state.get("openapitoken")
    selected_model = st.session_state.get("selected_model")

    preview_data = {}
    for column in df.columns:
        preview_data[column] = preview_df[column].tolist()
        preview_data[f"{column}_json"] = [
            run_inference(text, request, required_schema, openaiapiurl, openapitoken, selected_model)
            for text in preview_df[column]
        ]

    interleaved_columns = []
    for col in df.columns:
        interleaved_columns += [col, f"{col}_json"]

    preview_result = pd.DataFrame(preview_data)[interleaved_columns]
    display_aggrid(preview_result, title="Preview Result")

# --- Run Batch Inference ---
if st.button("Run"):
    timestart = time.time()
    request = st.session_state.get('request')
    required_schema = st.session_state.get('required_schema')
    openaiapiurl = st.session_state.get('openaiapiurl')
    openapitoken = st.session_state.get('openapitoken')
    selected_model = st.session_state.get('selected_model')

    missing_keys = [k for k in ['request', 'required_schema', 'openaiapiurl', 'openapitoken', 'selected_model'] if not st.session_state.get(k)]
    if missing_keys:
        st.error(f"Missing configuration keys: {', '.join(missing_keys)}")
        st.stop()

    total_texts = len(df) * len(df.columns)
    progress = st.progress(0)
    timer_display = st.empty()
    progress_counter = 0
    processed_columns = {f"{col}_json": [] for col in df.columns}

    def process_text(column, text):
        result = run_inference(text, request, required_schema, openaiapiurl, openapitoken, selected_model)
        return column, result

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for col in df.columns:
            for text in df[col]:
                futures.append(executor.submit(process_text, col, text))

        for i, future in enumerate(as_completed(futures)):
            col, result = future.result()
            processed_columns[f"{col}_json"].append(result)
            progress_counter += 1
            progress.progress(progress_counter / total_texts)
            timer_display.text(f"Elapsed Time: {time.time() - timestart:.2f} seconds")

    processed_df = pd.DataFrame(processed_columns)
    st.session_state.jprocessed_df = processed_df
    st.session_state.jprocessing_complete = True
    st.success("Processing completed!")

# --- Output ---
if 'jprocessed_df' in st.session_state:
    processed_df = st.session_state.jprocessed_df
    if append_mode:
        output_df = df.copy()
        for col in df.columns:
            output_df[f"{col}_json"] = processed_df[f"{col}_json"]
    else:
        output_df = processed_df

    display_aggrid(output_df, title="Processed Result")

    st.subheader("Download Processed Data")
    original_file_name = st.session_state.get("original_file", "processed_data").rsplit('.', 1)[0]
    base_name = f"{original_file_name}_{'appended' if append_mode else 'json'}"
    download_processed_files(output_df, base_name)