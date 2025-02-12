import streamlit as st

# Print available secrets
st.write("Available secrets:", st.secrets.keys())

# Check for sheet_id
if 'sheet_id' in st.secrets:
    st.success(f"✅ Found sheet_id: {st.secrets.sheet_id[:5]}...")
else:
    st.error("❌ sheet_id not found in secrets")

# Check for gcp_service_account
if 'gcp_service_account' in st.secrets:
    st.success("✅ Found gcp_service_account")
    # Print available fields
    st.write("GCP service account fields:", st.secrets.gcp_service_account.keys())
else:
    st.error("❌ gcp_service_account not found in secrets")