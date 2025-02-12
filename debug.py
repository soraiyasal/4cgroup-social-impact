import streamlit as st
import os

# First, let's check if we can read the secrets file
st.write("Current working directory:", os.getcwd())
st.write("Files in .streamlit:", os.listdir('.streamlit') if os.path.exists('.streamlit') else "No .streamlit folder found")

# Check if secrets are loaded
st.write("Available secrets:", st.secrets.keys() if hasattr(st, 'secrets') else "No secrets found")

# Try to access specific secrets
if 'gcp_service_account' in st.secrets:
    st.write("GCP service account found!")
    st.write("Project ID:", st.secrets.gcp_service_account.project_id)
else:
    st.write("No GCP service account in secrets")

if 'sheet_id' in st.secrets:
    st.write("Sheet ID found:", st.secrets.sheet_id)
else:
    st.write("No sheet_id in secrets")