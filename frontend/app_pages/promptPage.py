import streamlit as st
import json
import os
import requests
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

#st.set_page_config(layout="wide")
API_URL = os.getenv("API_URL")
API_PORT = os.getenv("API_PORT")

# default_prompt = """You are a helpful assistant. Classify the following content into positive, negative or neutral sentiment and provide an explanation for your choice.
# """

default_prompt='''You are a helpful assistant. '''

default_prompt_format = [
    {"type": "text", "name": "sentiment", "value": "positive", "description": "positive, negative or neutral"},
    {"type": "text", "name": "explanation", "value": "The phrase expresses a positive sentiment, indicating the speaker is delighted", "description": "reason for classification"}
]


# OUTPUT FORMAT
# sessions
if 'prompt_value' not in st.session_state:
    st.session_state.prompt_value = default_prompt

if 'fields' not in st.session_state:
    st.session_state.fields = default_prompt_format  # Store temporary fields

if 'prompt_format' not in st.session_state:
    #st.session_state.prompt_format = {}
    
    # for field in st.session_state.fields:
    #     if field["name"]:
    #         st.session_state.prompt_format[field["name"]] = field["value"]
    st.session_state.prompt_format = """You will reply in this format: {"sentiment": "{{positive, negative, or neutral}}", "explanation": "{{reason for classification}}"}
    \n\n<example>{"sentiment": "positive", "explanation": "The phrase expresses a positive sentiment, indicating the speaker is delighted"}<example/>
    """

if 'prompt_form_submitted' not in st.session_state:
    st.session_state.prompt_form_submitted = False
if 'prompt_json_submitted' not in st.session_state:
    st.session_state.prompt_json_submitted = False

if 'schema_prompt_value' not in st.session_state:
    st.session_state.schema_prompt_value = ''
    
@st.dialog("Error!")
def error_popup(e):
    st.write(f"{e}")
    refresh_button = st.button("Got it!")
    if refresh_button:
        st.rerun()

# backend_url = "http://localhost:8000/prompt-page"
backend_url = os.getenv("BACKEND_PROMPT_URL")

def prompt_page(openaiapi, schema_prompt_value, prompt_form_submitted):
    """
    Sends the PDF to the FastAPI backend and returns the translated file.
    """
    try:
        # Prepare the files and parameters for the request
        data = {
            'openaiapi': openaiapi,
            'schema_prompt_value': schema_prompt_value,
            'prompt_form_submitted': prompt_form_submitted,
            'url': st.session_state.openaiapiurl,
            'authorization':st.session_state.openapitoken,
            'model_name':st.session_state['selected_model']
        }

        print(data)

        # Send the request to the backend
        response = requests.post(backend_url, data=data)

        # Handle the response
        if response.status_code == 200:
            return response.json()  # The generated schema
        else:
            st.error(f"Error: {response.text}")
            return None
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None
        

# Set the title of the app
st.title('JSON Mode Schema Builder')
st.header('Prompt')

# Create a form
with st.form(key='prompt'):
    # name = st.text_input("Name")
    # age = st.number_input("Age", min_value=0, max_value=120)
    # hobby = st.selectbox("Select a hobby", ["Reading", "Gaming", "Cooking", "Traveling"])
    text_value_prompt = st.text_area("Prompt -> What you want the LLM to do?", value = st.session_state.prompt_value, height=300)

    # Submit button
    submit_button_prompt = st.form_submit_button(label='Update')

# Handle form submission
if submit_button_prompt:
    st.session_state.prompt_form_submitted = True
    st.session_state.prompt_value = text_value_prompt
    st.success("Prompt Updated successfully!")

# Title of the app
st.title("JSON Format")

with st.form(key='schema'):
    # Text area for user input
    
    text_value_schema = st.text_input("How do you want your output JSON to look like?", key="text_input_schema")
    
    # Submit button
    submit_button_schema = st.form_submit_button(label="Auto Generate Schema")

    if submit_button_schema:
        ans = prompt_page(st.session_state.openaiapi, str(text_value_schema), st.session_state.prompt_form_submitted)
        st.write("Response:", ans)  # Display the response
        if ans:
            st.session_state.api_response = ans 
        
   
if 'api_response' in st.session_state:
    use_schema = st.button("Use Generated Schema")
    if use_schema:
        response_data = st.session_state.api_response
        # st.write(response_data['columns'])
        # st.json(st.session_state.fields)
        response_list = []
        for tempdict in response_data['columns']:
            tempdict["name"] = tempdict.pop('column_name')
            tempdict["type"] = tempdict.pop('column_type')
            tempdict["value"] = tempdict.pop('example')
            tempdict["description"] = tempdict.pop('reasoning')
            if tempdict["type"] == "string":
                tempdict["type"] = "text"
            if tempdict["type"] == "integer" or tempdict["type"] == "float":
                tempdict["type"] = "number"
            response_list.append(tempdict)
        st.json(response_list)
        st.session_state.fields = response_list 
        st.session_state.pop('api_response')
        st.rerun()
# Display dynamic fields for the current JSON structure
if st.session_state.fields:
    st.write("Current Fields:")

    # Loop over fields to display appropriate input based on the field type, wrapped in containers
    for i, field in enumerate(st.session_state.fields):
        with st.container(border=True):
            st.write(f"Field {i+1}:")

            col1, col2, col3 = st.columns([4, 4, 1])

            with col1:
                # Field name
                field_name = st.text_input(f"Field {i+1} Name", value=field["name"], key=f"name_{i}")
                st.session_state.fields[i]["name"] = field_name


            with col2:
                # Field type selection (dropdown)
                field_type = st.selectbox(f"Field {i+1} Type", ['text', 'number', 'boolean'], #removed list and objects for now since outlines doesnt recognise it
                                          index=['text', 'number', 'boolean'].index(field["type"]), 
                                          key=f"type_{i}")
                st.session_state.fields[i]["type"] = field_type

            with col2:

                # Field value based on the selected type
                if field["type"] == "text":
                    field_value = st.text_area(f"Example Text {i+1} Value", value=field["value"], key=f"value_text_{i}",height=100)
                    st.session_state.fields[i]["value"] = field_value

                elif field["type"] == "number":
                    if type(field["value"]) not in [float,int]:
                        field["value"] = float(0)
                    field_value = st.number_input(f"Example Number {i+1} Value", value=field["value"], key=f"value_num_{i}")
                    st.session_state.fields[i]["value"] = field_value

                elif field["type"] == "boolean":
                    if not isinstance(field["value"], bool):
                        field["value"] = True
                    field_value = st.selectbox(f"Example Boolean {i+1} Value", [True, False], index=int(field["value"]), key=f"value_bool_{i}")
                    st.session_state.fields[i]["value"] = field_value

                elif field["type"] == "list":
                    if not isinstance(field["value"], list):
                        field["value"] = []
                    field_value = st.text_area(f"Example List {i+1} Values (comma-separated)", value=",".join(field["value"]), key=f"value_list_{i}")
                    st.session_state.fields[i]["value"] = list(map(str.strip, field_value.split(',')))

                elif field["type"] == "object":
                    field_value = st.text_area(f"Example Object {i+1} Value (JSON)", value=json.dumps(field["value"], indent=2), key=f"value_obj_{i}")
                    try:
                        st.session_state.fields[i]["value"] = json.loads(field_value)
                    except json.JSONDecodeError:
                        st.error(f"Invalid JSON format in Object Field {i+1}")

            with col1:
                field_value = st.text_area(f"Description of field {i+1}", value=field["description"], key=f"value_description_{i}",height=100)
                st.session_state.fields[i]["description"] = field_value

            with col3:
                # Button to remove field
                remove_button = st.button("Remove", key=f"remove_{i}")
                if remove_button:
                    st.session_state.fields.pop(i)
                    st.rerun()  # Rerun the app to update the UI after removal
    
with st.container():
    # Add a button to add a new dynamic row (field)
    if st.button("Add New Field"):
        st.session_state.fields.append({"type": "text", "name": "", "value": "", "description": ""})  # Default new field is 'text'
        st.rerun()
    # Optionally, allow the user to reset the JSON structure and fields
    if st.button("Reset JSON to default"):
        st.session_state.fields = default_prompt_format
        st.session_state.prompt_format = {}
        st.success("JSON structure reset!")
        st.rerun()
    
# Button to generate the JSON output
if st.button("Update JSON"):
    # Build the final JSON data based on current fields
    st.session_state.prompt_format = {}
    format_template = {}
    format_example = {}
    headerlist = []
    for field in st.session_state.fields:
        if field["name"]:  # Ensure the field name is provided  
            st.session_state.prompt_format[field["name"]] = field["value"]
            format_template[field["name"]] = f"{{{{{field['description']}}}}}"
            format_example[field["name"]] = field["value"]

            header = {
                    "column_name":field["name"],
                    "column_type":field["type"]
                }
            if header["column_type"] == "text":
                header["column_type"] = "string"
            if header["column_type"] == "number":
                header["column_type"] = "number"
            headerlist.append(header)
            
    
    st.session_state.required_schema = headerlist
    st.success("JSON generated and updated successfully!")
    st.json(st.session_state.prompt_format)
    st.session_state.prompt_format = f"You will reply in this format:\n{json.dumps(format_template)}\n\n<example>{json.dumps(format_example)}<example/>"
    st.session_state.request=f"{st.session_state.prompt_value}\n\nYou will reply in this format:\n{json.dumps(format_template)}\n\n<example>{json.dumps(format_example)}<example/>"
    # st.write(st.session_state.prompt_format)
    st.write(st.session_state.request)