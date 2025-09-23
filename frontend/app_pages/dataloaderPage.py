import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
from streamlit_pdf_viewer import pdf_viewer

st.title("Data Loader")

# Display processing limits info
st.info("📋 **Processing Limits:** Maximum file size: 5GB | Processing timeout: 4 hours for large documents")

# Initialize session state
if "data_loaded" not in st.session_state:
    st.session_state.clear()

# File uploader
uploaded_file = st.file_uploader("Upload a file", type=["csv", "xlsx", "pdf"])

if uploaded_file:
    # Read the uploaded file into a DataFrame
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)

    # Store the uploaded file in session state for future use
    st.session_state.original_file = uploaded_file.name
    if uploaded_file.name.endswith(".pdf"):
        with st.spinner("Processing PDF file..."):
            try:
                # Attempt to access the file content to ensure it's fully loaded
                file_size = len(uploaded_file.getvalue())
                st.session_state.pdf = uploaded_file
                st.success(f"PDF successfully loaded! ({file_size:,} bytes) Ready for processing.")
            except Exception as e:
                st.error(f"Error processing PDF file: {e}")
                st.info("Please try uploading the file again.")

        # Optional PDF preview (can be slow for large files)
        if st.checkbox("Preview PDF (may be slow for large files)", value=False):
            with st.spinner("Loading PDF preview..."):
                try:
                    binary_data = st.session_state.pdf.getvalue()
                    pdf_viewer(input=binary_data, width=700)
                except Exception as e:
                    st.error(f"Could not render PDF preview: {e}")
                    st.info("PDF file loaded successfully but preview failed. You can still proceed with translation.")
    else:
        # Display the uploaded file content using AgGrid
        st.subheader("Uploaded File Contents")
        
        # Show only first 100 rows initially
        preview_df = df.head(100)
        
        # Configure AgGrid options
        gb = GridOptionsBuilder.from_dataframe(preview_df)
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_side_bar()
        gb.configure_default_column(wrapText=True, autoHeight=True)
        grid_options = gb.build()

        # Render the grid
        AgGrid(
            preview_df,
            gridOptions=grid_options,
            enable_enterprise_modules=False,
            theme="streamlit",
            fit_columns_on_grid_load=True,
        )

        # Allow column selection
        selected_columns = st.multiselect("Select columns for LLM processing", df.columns.tolist(), [])
        if selected_columns:
            st.session_state.original_df = df
            st.session_state.selected_df = df[selected_columns]
            st.session_state.selected_columns = selected_columns
            st.session_state.data_loaded = True

            # After column selection, display the full dataset
            full_df = df[selected_columns]
            st.subheader("Selected Columns for Processing (Full Data)")
            
            # Configure AgGrid options for full data
            selected_gb = GridOptionsBuilder.from_dataframe(full_df)
            selected_gb.configure_pagination(paginationAutoPageSize=True)
            selected_gb.configure_default_column(wrapText=True, autoHeight=True)
            selected_grid_options = selected_gb.build()

            AgGrid(
                full_df,
                gridOptions=selected_grid_options,
                enable_enterprise_modules=False,
                theme="streamlit",
                fit_columns_on_grid_load=True,
            )

            # Append or save mode toggle
            st.subheader("Save Options")
            st.session_state.append_mode = st.checkbox("Append processed output to original file", value=False)
            if st.session_state.append_mode:
                st.info("Processed output will be appended to the original file.")
            else:
                st.info("Processed output will be saved as a new file.")

            st.success("Data successfully loaded and prepared for processing!")
        else:
            st.warning("Please select at least one column.")
else:
    st.info("Upload a file to begin.")
