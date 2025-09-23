import io
import requests
import streamlit as st
import pandas as pd
import json
# Replace st_aggrid with st.dataframe if AgGrid causes issues
from st_aggrid import AgGrid, GridOptionsBuilder

from dotenv import load_dotenv
import os
# Load environment variables from .env file
load_dotenv()
API_URL = os.getenv("API_URL")
API_PORT = os.getenv("API_PORT")

# Use modern Streamlit caching
cache_function = st.cache_data

if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = ""
if "user_prompt" not in st.session_state:
    st.session_state.user_prompt = ""
    
@st.dialog("Error!")
def error_popup(e):
    st.write(f"{e}")
    refresh_button = st.button("Got it!")
    if refresh_button:
        st.rerun()

def process_with_model(text, system_prompt, user_prompt):
    try:
            # Prepare the files and parameters for the request
            # FastAPI backend URL
            # backend_url = "http://localhost:8000/free-processing"
            backend_url = os.getenv("BACKEND_FREE_URL")

            data = {
                'text': text,
                'system_prompt': system_prompt,
                'user_prompt': user_prompt,
                'url': st.session_state.openaiapiurl,
                'authorization':st.session_state.openapitoken,
                'model_name':st.session_state['selected_model']
            }

            print(data)

            # Send the request to the backend
            response = requests.post(backend_url, data=data)

            # Handle the response
            if response.status_code == 200:
                return response.content  # The free processing content
            else:
                st.error(f"Error: {response.text}")
                return None
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# Function to load configuration from uploaded file
def load_config(uploaded_file):
    try:
        config = json.load(uploaded_file)
        st.session_state.system_prompt = config.get('system_prompt', '')
        st.session_state.user_prompt = config.get('user_prompt', '')
        st.success('Configuration loaded successfully.')
    except Exception as e:
        st.error(f'Failed to load configuration: {e}')

st.title("Free Processing")

# Check if a DataFrame is loaded
if 'selected_df' not in st.session_state or st.session_state.selected_df is None:
    st.warning("No data loaded. Please go to the Data Loader page and upload a file.")
    if st.button("Run single inference") or 'single_inference' in st.session_state:
        st.session_state.single_inference = True
        # Prompt settings
        st.subheader("Prompt Settings")
        uploaded_config = st.file_uploader('Upload a configuration file', type="json.config")
        if uploaded_config is not None:
            load_config(uploaded_config)

        with st.container():
            system_prompt = st.text_area(
                "System Prompt",
                placeholder="Describe the role the LLM will take (e.g., You are a helpful sentiment analyst.). Leaving this blank will default to 'You are a helpful assistant'.",
                max_chars=1024,
                value=st.session_state.system_prompt
            )
            user_prompt = st.text_area(
                "User Prompt",
                placeholder="Describe how you want the LLM to process your text. (e.g., Categorize the following into positive, neutral or negative sentiment)",
                max_chars=1024,
                value=st.session_state.user_prompt
            )

            # Calculate total characters used (excluding the dynamic text from df)
            total_chars = len(system_prompt) + len(user_prompt) + 2  # +2 for ": "
            st.write(f"Total characters used: {total_chars}/2048")

            if total_chars > 2048:
                st.warning( "The combined length of System Prompt and User Prompt should be less than or equal to 2048 characters.")


        text = st.text_area("Input Data")
        
        if st.button("Run"):
            if total_chars > 2048:
                st.warning("Cannot proceed: The combined length of System Prompt and User Prompt exceeds 2048 characters.")
            else:
                # Run the full processing and generate a processed DataFrame
                st.subheader("Result")
                
                st.write(process_with_model(text, system_prompt, user_prompt))

                st.success("Processing completed!")

        st.subheader("Save Prompt")
        config_payload = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }
        
        st.write("Current Prompt:", config_payload)

        if user_prompt!="":
        # Input for configuration name
            config_name = st.text_input('Enter a name for the configuration (used for the filename):', '')

            if st.button('Save Configuration'):
                if config_name.strip() == '':
                    st.error('Please enter a configuration name to save.')
                else:
                    config_json = json.dumps(config_payload, indent=4)
                    config_filename = f"{config_name.strip().replace(' ', '_')}.json.config"
                    st.download_button(
                        label="Download Configuration",
                        data=config_json,
                        file_name=config_filename,
                        mime="application/json"
                    )
else:
        
    # Display the currently loaded DataFrame using AgGrid or st.dataframe
    df = st.session_state.selected_df
    st.subheader("Loaded DataFrame")

    # If AgGrid causes issues, use st.dataframe instead
    try:
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_side_bar()
        gb.configure_default_column(wrapText=True, autoHeight=True)
        grid_options = gb.build()

        AgGrid(df, gridOptions=grid_options, enable_enterprise_modules=False, theme="streamlit", fit_columns_on_grid_load=True)
    except AttributeError:
        st.dataframe(df)

    # Prompt settings
    st.subheader("Prompt Settings")

    uploaded_config = st.file_uploader('Upload a configuration file', type="json.config")
    if uploaded_config is not None:
        load_config(uploaded_config)
        #st.rerun(scope = "fragment")
        st.rerun()

    system_prompt = st.text_area(
        "System Prompt",
        placeholder="Describe the role the LLM will take (e.g., You are a helpful sentiment analyst.). Leaving this blank will default to 'You are a helpful assistant'.",
        max_chars=1024,
        value=st.session_state.system_prompt
    )
    user_prompt = st.text_area(
        "User Prompt",
        placeholder="Describe how you want the LLM to process your text. (e.g., Categorize the following into positive, neutral or negative sentiment)",
        max_chars=1024,
        value=st.session_state.user_prompt
    )

    # Calculate total characters used (excluding the dynamic text from df)
    total_chars = len(system_prompt) + len(user_prompt) + 2  # +2 for ": "
    st.write(f"Total characters used: {total_chars}/2048")

    if total_chars > 2048:
        st.warning("The combined length of System Prompt and User Prompt should be less than or equal to 2048 characters.")



    # Indicate save option to the user
    st.subheader("Save Options")
    if 'append_mode' in st.session_state:
        append_mode = st.session_state.append_mode
    else:
        append_mode = False  # Default to False if not set

    if append_mode:
        st.info("Processed output will be appended to the original file.")
    else:
        st.info("Processed output will be saved as a new file.")

    # Preview and Run Buttons
    if st.button("Preview"):
        if total_chars > 2048:
            st.warning("Cannot proceed: The combined length of System Prompt and User Prompt exceeds 2048 characters.")
        else:
            # Generate a preview with random rows for each column
            st.subheader("Processing Preview")

            sample_size = min(5, len(df))  # Ensure sample size does not exceed the number of rows
            preview_df = df.sample(n=sample_size)
            preview_data = {}
            for column in df.columns:
                processed_column_name = f"{column}_processed"
                preview_data[column] = preview_df[column].tolist()
                preview_data[processed_column_name] = [
                    process_with_model(text, system_prompt, user_prompt) for text in preview_df[column]
                ]

            # Arrange columns side by side
            interleaved_columns = []
            for column in df.columns:
                processed_column_name = f"{column}_processed"
                interleaved_columns.extend([column, processed_column_name])

            preview_result = pd.DataFrame(preview_data)[interleaved_columns]

            # Display the preview using AgGrid or st.dataframe
            st.subheader("Preview Result")
            try:
                gb_preview = GridOptionsBuilder.from_dataframe(preview_result)
                gb_preview.configure_pagination(paginationAutoPageSize=True)
                gb_preview.configure_default_column(wrapText=True, autoHeight=True)
                preview_grid_options = gb_preview.build()

                AgGrid(preview_result, gridOptions=preview_grid_options, enable_enterprise_modules=False, theme="streamlit", fit_columns_on_grid_load=True)
            except AttributeError:
                st.dataframe(preview_result)

    if st.button("Run"):
        if total_chars > 2048:
            st.warning("Cannot proceed: The combined length of System Prompt and User Prompt exceeds 2048 characters.")
        else:
            # Run the full processing and generate a processed DataFrame
            st.subheader("Processing Data...")

            processed_data = {}
            total_texts = len(df) * len(df.columns)
            progress = st.progress(0)
            progress_counter = 0

            for column in df.columns:
                processed_column_name = f"{column}_processed"
                processed_texts = []
                for text in df[column]:
                    processed_text = process_with_model(text, system_prompt, user_prompt)
                    processed_texts.append(processed_text)
                    progress_counter += 1
                    progress.progress(progress_counter / total_texts)
                processed_data[processed_column_name] = processed_texts

            processed_df = pd.DataFrame(processed_data)
            st.session_state.processed_df = processed_df  # Store the processed DataFrame in session state
            st.session_state.processing_complete = True
            st.success("Processing completed!")

    # Check if processed_df exists in session state
    if 'processed_df' in st.session_state:
        processed_df = st.session_state.processed_df

        # Determine the output DataFrame based on append_mode
        if append_mode:
            # Combine the original DataFrame and the processed columns side by side
            output_df = pd.DataFrame()
            original_df = st.session_state.original_df
            for column in original_df.columns:
                processed_column_name = f"{column}_processed"
                output_df[column] = original_df[column]
                #output_df[processed_column_name] = processed_df[processed_column_name]
                if processed_column_name in processed_df.columns:
                    output_df[processed_column_name] = processed_df[processed_column_name]
        else:
            # Use only the processed DataFrame
            output_df = processed_df

        # Display the output DataFrame using AgGrid or st.dataframe
        st.subheader("Processed Result")
        try:
            gb_processed = GridOptionsBuilder.from_dataframe(output_df)
            gb_processed.configure_pagination(paginationAutoPageSize=True)
            gb_processed.configure_default_column(wrapText=True, autoHeight=True)
            processed_grid_options = gb_processed.build()

            AgGrid(output_df, gridOptions=processed_grid_options, enable_enterprise_modules=False, theme="streamlit", fit_columns_on_grid_load=True)
        except AttributeError:
            st.dataframe(output_df)

        # Provide download options
        st.subheader("Download Processed Data")

        # Convert DataFrame to various formats
        csv_buffer = output_df.to_csv(index=False).encode('utf-8')
        json_buffer = output_df.to_json(orient='records', indent=2).encode('utf-8')

        # Create an Excel file in-memory
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            output_df.to_excel(writer, index=False, sheet_name='Processed_Data')
            # The context manager saves the file automatically

        # Prepare file name based on original file name and append mode
        if 'original_file' in st.session_state and st.session_state.original_file:
            original_file_name = st.session_state.original_file.rsplit('.', 1)[0]
        else:
            original_file_name = 'processed_data'

        if append_mode:
            csv_file_name = f"{original_file_name}_appended.csv"
            json_file_name = f"{original_file_name}_appended.json"
            excel_file_name = f"{original_file_name}_appended.xlsx"
        else:
            csv_file_name = f"{original_file_name}_processed.csv"
            json_file_name = f"{original_file_name}_processed.json"
            excel_file_name = f"{original_file_name}_processed.xlsx"

        # Add download buttons
        st.download_button(
            label="Download as CSV",
            data=csv_buffer,
            file_name=csv_file_name,
            mime="text/csv"
        )
        st.download_button(
            label="Download as JSON",
            data=json_buffer,
            file_name=json_file_name,
            mime="application/json"
        )
        st.download_button(
            label="Download as Excel",
            data=excel_buffer.getvalue(),
            file_name=excel_file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.subheader("Save Prompt")

    config_payload = {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }
    st.write("Current Prompt:", config_payload)

    if user_prompt!="":
    # Input for configuration name
        config_name = st.text_input('Enter a name for the configuration (used for the filename):', '')

        if st.button('Save Configuration'):
            if config_name.strip() == '':
                st.error('Please enter a configuration name to save.')
            else:
                config_json = json.dumps(config_payload, indent=4)
                config_filename = f"{config_name.strip().replace(' ', '_')}.json.config"
                st.download_button(
                    label="Download Configuration",
                    data=config_json,
                    file_name=config_filename,
                    mime="application/json"
                )
