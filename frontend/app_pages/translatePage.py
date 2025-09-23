import io 
import requests
import streamlit as st
import pandas as pd
# Replace st_aggrid with st.dataframe if AgGrid causes issues
from st_aggrid import AgGrid, GridOptionsBuilder
import time
from dotenv import load_dotenv
import os
import numpy as np

# Use the appropriate caching decorator based on your Streamlit version
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

st.title("Translation Page")

# Check if a DataFrame is loaded
if 'selected_df' not in st.session_state or st.session_state.selected_df is None:
    st.warning("No data loaded. Please go to the Data Loader page and upload a file.")
    if st.button("Run single inference") or 'single_inference' in st.session_state:
        st.session_state.single_inference = True
        # Language selection
        st.subheader("Translation Settings")
        input_language = st.selectbox("Select Input Language (optional)", options=[""] + LANGCODES, format_func=lambda x: "Automatic" if x == "" else x)
        output_language = st.selectbox("Select Output Language", options=LANGCODES)

        # Translation prompt generation
        st.subheader("Generated Translation Prompt")

        if input_language:
            user_prompt = f"Translate the following text into {output_language} directly, without altering the original meaning. Keep all numbers, math equations, symbols, unicode, and formatting (e.g., blank lines, dashes) intact. Do not add interpretations, summaries, or personal perspectives. The translation should be natural, accurate, clean, and faithful to the original text."
        else:
            user_prompt = f"Translate the following {input_language} text into {output_language} directly, without altering the original meaning. Keep all numbers, math equations, symbols, unicode, and formatting (e.g., blank lines, dashes) intact. Do not add interpretations, summaries, or personal perspectives. The translation should be natural, accurate, clean, and faithful to the original text."

        st.write('User Prompt:',user_prompt)

        with st.form(key='single_inference_form'):
            
            text = st.text_area("Input Text")
            translate_button = st.form_submit_button("Submit")
        if translate_button:
            try:
                # url = f"http://localhost:8000/translate"
                url = os.getenv("BACKEND_TRANSLATE_URL")
                response = requests.post(url, json={
                    "text": text,
                    "input_language": input_language,
                    "output_language": output_language,
                    'url': st.session_state.openaiapiurl,
                    'authorization': st.session_state.openapitoken,
                    'translation_model_name': st.session_state['selected_model']
                })
                
                if response.status_code == 200:
                    translated_text = response.content
                    st.header("Result")
                    # st.write(translated_text)
                else:
                    st.error("Error in translation request: " + response.text)
            except Exception as e:
                st.error(f"Error in translation request: {e}")
    
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

    # Language selection
    st.subheader("Translation Settings")
    input_language = st.selectbox("Select Input Language (optional)", options=[""] + LANGCODES, format_func=lambda x: "Automatic" if x == "" else x)
    output_language = st.selectbox("Select Output Language", options=LANGCODES)

    # Translation prompt generation
    st.subheader("Generated Translation Prompt")

    if input_language:
        user_prompt = f"Translate the following text into {output_language} directly, without altering the original meaning. Keep all numbers, math equations, symbols, unicode, and formatting (e.g., blank lines, dashes) intact. Do not add interpretations, summaries, or personal perspectives. The translation should be natural, accurate, clean, and faithful to the original text."
    else:
        user_prompt = f"Translate the following {input_language} text into {output_language} directly, without altering the original meaning. Keep all numbers, math equations, symbols, unicode, and formatting (e.g., blank lines, dashes) intact. Do not add interpretations, summaries, or personal perspectives. The translation should be natural, accurate, clean, and faithful to the original text."

        st.write('User Prompt:',user_prompt)
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


    # if st.button("Preview"):
    #     # Generate a preview with random rows for each column
    #     breakflag = False

    #     sample_size = min(5, len(df))  # Ensure sample size does not exceed the number of rows
    #     preview_df = df.sample(n=sample_size)
    #     preview_data = {}

    #     # Process all columns
    #     for column in df.columns:
    #         # if df[column].dtype == 'object' and pd.api.types.is_string_dtype(df[column]):
    #         if df[column].dtype == 'object' and df[column].apply(lambda x: isinstance(x, str) or pd.isna(x)).all():
    #             # print(f"Processing column: {column}")
    #             st.write(f"Processing column: {column}")
    #             translated_column_name = f"{column}_translated"
    #             preview_data[column] = preview_df[column].tolist()  # Add the original column data

    #             # Translate only string columns
    #             translated_texts = []
    #             for text in preview_df[column]:
    #                 # Call the FastAPI backend to get translation
    #                 # url = f"http://localhost:8000/translate"
    #                 url = os.getenv("BACKEND_TRANSLATE_URL")
    #                 headers = {"Content-Type": "application/json"}
    #                 # print(text)
    #                 data = {
    #                     "text": text,  # Original text to translate
    #                     "input_language": input_language,  # The language of the original text
    #                     "output_language": output_language,  # The desired output language
    #                     "user_prompt": "Translate the following text",  # You can adjust this as needed
    #                     "url": st.session_state.openaiapiurl + "/v1/chat/completions",  # URL to the OpenAI API
    #                     "authorization": st.session_state.openapitoken,  # Authorization token for the OpenAI API
    #                     "translation_model_name": st.session_state['selected_model']  # Selected model for translation
    #                 }

    #                 response = requests.post(url, json=data, headers=headers)

    #                 if response.status_code == 200:
    #                     translated_text = response.json().get("translated_text", "")
    #                     translated_texts.append(translated_text)
    #                 else:
    #                     translated_texts.append("Error in translation")

    #             preview_data[translated_column_name] = translated_texts  # Add translated column

    #         else:
    #             # Directly add non-string columns without translation
    #             preview_data[column] = preview_df[column].tolist()

    #     if breakflag == False:
    #         st.subheader("Translation Preview")
            
    #         # List to store the interleaved column names (original + translated)
    #         interleaved_columns = []

    #         # Iterate through each column in the dataframe
    #         for column in df.columns:
    #             # Add the original column to the list first
    #             interleaved_columns.append(column)

    #             # For string columns, add the translated column if it exists
    #             if df[column].dtype == 'object' and pd.api.types.is_string_dtype(df[column]):
    #                 translated_column_name = f"{column}_translated"
    #                 interleaved_columns.append(translated_column_name)

    #         # Create the preview DataFrame with all original columns + translated columns where applicable
    #         preview_result = pd.DataFrame(preview_data)[interleaved_columns]

    #         # Display the preview using AgGrid or st.dataframe
    #         st.subheader("Preview Result")
    #         try:
    #             gb_preview = GridOptionsBuilder.from_dataframe(preview_result)
    #             gb_preview.configure_pagination(paginationAutoPageSize=True)
    #             gb_preview.configure_default_column(wrapText=True, autoHeight=True)
    #             preview_grid_options = gb_preview.build()

    #             AgGrid(preview_result, gridOptions=preview_grid_options, enable_enterprise_modules=False, theme="streamlit", fit_columns_on_grid_load=True)
    #         except AttributeError:
    #             st.dataframe(preview_result)

    if st.button("Preview"):
        # Generate a preview with random rows for each column
        breakflag = False

        sample_size = min(5, len(df))  # Ensure sample size does not exceed the number of rows
        preview_df = df.sample(n=sample_size)
        preview_data = {}

        # Process all columns
        for column in df.columns:
            if df[column].dtype == 'object' and df[column].apply(lambda x: isinstance(x, str) or pd.isna(x)).all():
                # Ensure NaN values are handled before translation
                # st.write(f"Processing column: {column}")
                translated_column_name = f"{column}_translated"
                preview_data[column] = preview_df[column].fillna("").tolist()  # Replace NaN with empty string

                # Translate only string columns
                translated_texts = []
                for text in preview_df[column].fillna(""):  # Ensure NaN is replaced with empty string for translation
                    # st.write(f"Translating: {text}") 
                    # Call the FastAPI backend to get translation
                    url = os.getenv("BACKEND_TRANSLATE_URL")
                    headers = {"Content-Type": "application/json"}
                    data = {
                        "text": text,  # Original text to translate
                        "input_language": input_language,  # The language of the original text
                        "output_language": output_language,  # The desired output language
                        "user_prompt": "Translate the following text",  # You can adjust this as needed
                        "url": st.session_state.openaiapiurl,  # URL to the OpenAI API
                        "authorization": st.session_state.openapitoken,  # Authorization token for the OpenAI API
                        "translation_model_name": st.session_state['selected_model']  # Selected model for translation
                    }

                    response = requests.post(url, json=data, headers=headers)

                    if response.status_code == 200:
                        translated_text = response.json().get("translated_text", "")
                        # st.write(translated_text)
                        translated_texts.append(translated_text)
                    else:
                        translated_texts.append("Error in translation")

                preview_data[translated_column_name] = translated_texts  # Add translated column

            else:
                # Directly add non-string columns without translation
                preview_data[column] = preview_df[column].fillna("").tolist()  # Replace NaN with empty string

        if breakflag == False:
            st.subheader("Translation Preview")

            # List to store the interleaved column names (original + translated)
            interleaved_columns = []

            # Iterate through each column in the dataframe
            for column in df.columns:
                # Add the original column to the list first
                interleaved_columns.append(column)

                # For string columns, add the translated column if it exists
                if df[column].dtype == 'object' and df[column].apply(lambda x: isinstance(x, str) or pd.isna(x)).all():
                    translated_column_name = f"{column}_translated"
                    interleaved_columns.append(translated_column_name)

            # Create the preview DataFrame with all original columns + translated columns where applicable
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
        # Run the full translation and generate a translated DataFrame
        st.subheader("Translating Data...")

        translated_data = {}
        total_texts = len(df) * len(df.columns)
        progress = st.progress(0)
        progress_counter = 0
        timestart = time.time()
        
        # Timer display
        timer_display = st.empty()  # To dynamically update the time
        
        # List to store the interleaved column names (original + translated)
        interleaved_columns = []

        for column in df.columns:
            if df[column].dtype == 'object' and df[column].apply(lambda x: isinstance(x, str) or pd.isna(x)).all():
            # if df[column].dtype == 'object' and pd.api.types.is_string_dtype(df[column]):
                print(f"Processing column: {column}")
                translated_column_name = f"{column}_translated"

                # translated_data[column] = df[column].tolist()  # Add the original column data
                translated_data[column] = df[column].fillna("").tolist() 
                translations = []
                
                # Translate only string columns
                # for text in df[column]:
                for text in df[column].fillna(""): 
                    # Call the FastAPI backend to get translation
                    # url = f"http://localhost:8000/translate"
                    url = os.getenv("BACKEND_TRANSLATE_URL")
                    headers = {"Content-Type": "application/json"}
                    # print(text)
                    data = {
                        "text": text,  # Original text to translate
                        "input_language": input_language,  # The language of the original text
                        "output_language": output_language,  # The desired output language
                        "user_prompt": "Translate the following text",  # You can adjust this as needed
                        "url": st.session_state.openaiapiurl,  # URL to the OpenAI API
                        "authorization": st.session_state.openapitoken,  # Authorization token for the OpenAI API
                        "translation_model_name": st.session_state['selected_model']  # Selected model for translation
                    }

                    response = requests.post(url, json=data, headers=headers)
                    
                    if response.status_code == 200:
                        translated_text = response.json().get("translated_text", "")
                        translations.append(translated_text)
                    else:
                        translations.append("Error in translation")

                    progress_counter += 1
                    progress.progress(progress_counter / total_texts)

                translated_data[translated_column_name] = translations
            else:
                # translated_data[column] = df[column].tolist()
                translated_data[column] = df[column].fillna("").tolist() 


        st.subheader("Translation Result")
        
        # List to store the interleaved column names (original + translated)
        interleaved_columns = []

        # Iterate through each column in the dataframe
        for column in df.columns:
            # Add the original column to the list first
            interleaved_columns.append(column)

            # For string columns, add the translated column if it exists
            # if df[column].dtype == 'object' and pd.api.types.is_string_dtype(df[column]):
            if df[column].dtype == 'object' and df[column].apply(lambda x: isinstance(x, str) or pd.isna(x)).all():
                translated_column_name = f"{column}_translated"
                interleaved_columns.append(translated_column_name)

        # Create the preview DataFrame with all original columns + translated columns where applicable
        preview_result = pd.DataFrame(translated_data)[interleaved_columns]
        st.session_state.preview_result = preview_result
        progress.progress(1.0)

    if 'preview_result' in st.session_state:
        preview_result = st.session_state.preview_result

        if append_mode:
            # Combine the original DataFrame and the translated columns side by side
            output_df = pd.DataFrame()
            original_df = st.session_state.original_df
            for column in original_df.columns:
                translated_column_name = f"{column}_translated"
                output_df[column] = original_df[column]
                #output_df[translated_column_name] = translated_df[translated_column_name]
                if translated_column_name in preview_result.columns:
                    output_df[translated_column_name] = preview_result[translated_column_name]  # Add the translated column
                    # st.session_state.output_df = output_df
        else:
            # Use only the translated DataFrame
            output_df = preview_result
            # st.session_state.output_df = output_df

        try:
            gb_preview = GridOptionsBuilder.from_dataframe(output_df)
            gb_preview.configure_pagination(paginationAutoPageSize=True)
            gb_preview.configure_default_column(wrapText=True, autoHeight=True)
            preview_grid_options = gb_preview.build()

            AgGrid(output_df, gridOptions=preview_grid_options, enable_enterprise_modules=False, theme="streamlit", fit_columns_on_grid_load=True)
        except AttributeError:
            st.dataframe(output_df)

    # if 'output_df' in st.session_state:
    #     output_df = st.session_state.output_df

        # Provide download options
        st.subheader("Download Translated Data")

        # Convert DataFrame to various formats
        csv_buffer = output_df.to_csv(index=False).encode('utf-8')
        # json_buffer = output_df.to_json(orient='records', indent=2).encode('utf-8')
        safe_output_df = output_df.replace({np.nan: None})  # Convert NaN to None for JSON serialization
        json_buffer = safe_output_df.to_json(orient='records', indent=2).encode('utf-8')


        # Create an Excel file in-memory
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            output_df.to_excel(writer, index=False, sheet_name='Translated_Data')
            # The context manager saves the file automatically

        # Prepare file name based on original file name and append mode
        if 'original_file' in st.session_state and st.session_state.original_file:
            original_file_name = st.session_state.original_file.rsplit('.', 1)[0]
        else:
            original_file_name = 'translated_data'

        if append_mode:
            csv_file_name = f"{original_file_name}_appended.csv"
            json_file_name = f"{original_file_name}_appended.json"
            excel_file_name = f"{original_file_name}_appended.xlsx"
        else:
            csv_file_name = f"{original_file_name}_translated.csv"
            json_file_name = f"{original_file_name}_translated.json"
            excel_file_name = f"{original_file_name}_translated.xlsx"

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

