import streamlit as st
import pandas as pd
import os
import re
import zipfile
import io
import tempfile
import shutil

# Set page config to wide mode
st.set_page_config(layout="wide")

@st.cache_data
def parse_question_updated(col):
    match = re.match(r'(\d+)\)\s*Q(\d+)(?:\.([a-zA-Z]))?', col)
    return (int(match.group(2)), match.group(3) if match.group(3) else '', int(match.group(1))) if match else (float('inf'), 'z', float('inf'))

@st.cache_data
def process_file(df):
    question_pattern = r'\d+\)\s*Q\d+(\.[a-zA-Z])?'
    sorted_question_columns = sorted(df.filter(regex=question_pattern).columns, key=parse_question_updated)
   
    value_columns = list(sorted_question_columns)
    if 'TotalObtainedScore' in df.columns:
        value_columns.append('TotalObtainedScore')
   
    id_columns = [col for col in df.columns if col not in value_columns]
   
    melted_df = pd.melt(df, id_vars=id_columns, value_vars=value_columns, var_name='Attribute', value_name='Value')
   
    def custom_sort(x):
        if x.name == 'Attribute':
            return pd.Series([parse_question_updated(val) for val in x])
        return x
    melted_df = melted_df.sort_values(id_columns + ['Attribute'], key=custom_sort)
   
    return melted_df

def main():
    st.title("Excel File Processor")
    
    uploaded_file = st.file_uploader("Upload a zip file containing Excel files", type="zip")
    
    if uploaded_file is not None:
        with tempfile.TemporaryDirectory() as tmpdirname:
            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                zip_ref.extractall(tmpdirname)
            
            excel_files = [f for f in os.listdir(tmpdirname) if f.endswith('.xlsx')]
            
            if not excel_files:
                st.warning("No Excel files found in the uploaded zip.")
                return
            
            progress_bar = st.progress(0)
            processed_dfs = []
            
            for i, filename in enumerate(excel_files):
                input_file = os.path.join(tmpdirname, filename)
                df = pd.read_excel(input_file)
                processed_df = process_file(df)
                processed_dfs.append((filename, processed_df))
                progress_bar.progress((i + 1) / len(excel_files))
            
            output_zip_buffer = io.BytesIO()
            with zipfile.ZipFile(output_zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zf:
                for filename, df in processed_dfs:
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                    zf.writestr(filename, excel_buffer.getvalue())
            
            st.success(f"All {len(excel_files)} files processed successfully!")
            
            st.download_button(
                label="Download processed files",
                data=output_zip_buffer.getvalue(),
                file_name="processed_files.zip",
                mime="application/zip"
            )

if __name__ == "__main__":
    main()
