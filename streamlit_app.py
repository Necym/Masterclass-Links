# 📦 Streamlit App: Search Language ➔ Show SCORM Review Links + Upload Mode

import streamlit as st
import os
import zipfile
import shutil
import tempfile
import urllib.parse
from b2sdk.v2 import InMemoryAccountInfo, B2Api

st.set_option('server.maxUploadSize', 1000)  # size in MB


# ─── Backblaze B2 Credentials ───
B2_KEY_ID = '0057d19983190740000000001'
B2_APP_KEY = 'K0050E3EGgdBJduyi+MOTBZZzk4Y+go'
BUCKET_ID = '774d61f9d938638199600714'
BUCKET_NAME = 'filesfornecym'
BASE_URL = f"https://f005.backblazeb2.com/file/{BUCKET_NAME}"

# ─── Connect to Backblaze ───
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", B2_KEY_ID, B2_APP_KEY)
bucket = b2_api.get_bucket_by_id(BUCKET_ID)

# ─── Streamlit GUI Setup ───
st.set_page_config(page_title="SCORM Review Links")
st.title("SCORM Review Link Generator")

mode = st.sidebar.radio("Choose Mode", ["View Links", "Upload New Language"])

if mode == "View Links":
    all_files = bucket.ls('')
    language_folders = set()
    for file_version_info, folder_name in all_files:
        if folder_name is not None:
            language = folder_name.strip('/').split('/')[0]
            language_folders.add(language)

    sorted_languages = sorted(list(language_folders))
    selected_language = st.selectbox("Select Language:", sorted_languages)

    if selected_language:
        subfolders = set()
        all_files = bucket.ls(f"{selected_language}/")
        for file_version_info, folder_name in all_files:
            if folder_name is not None:
                parts = folder_name.strip('/').split('/')
                if len(parts) >= 2:
                    subfolders.add(parts[1])

        sorted_scorms = sorted(list(subfolders))

        if sorted_scorms:
            st.subheader(f"SCORM Packages in {selected_language}:")
            for scorm_folder in sorted_scorms:
                encoded_folder = urllib.parse.quote(scorm_folder)
                display_name = scorm_folder.replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('\\', '\\\\')
                review_link = f"{BASE_URL}/{selected_language}/{encoded_folder}/story.html"
                st.markdown(f"[📄 {display_name}]({review_link})")
        else:
            st.info(f"No SCORM courses found inside {selected_language}.")

elif mode == "Upload New Language":
    language_name = st.text_input("Enter new language folder name (e.g., Arabic)")

    if language_name:
        # Check if language already exists
        all_files = bucket.ls('')
        existing_languages = set()
        for file_version_info, folder_name in all_files:
            if folder_name is not None:
                existing_languages.add(folder_name.strip('/').split('/')[0])

        if language_name in existing_languages:
            confirm_delete = st.checkbox(f"⚠️ '{language_name}' already exists. Check to confirm deletion of existing content.")
            if confirm_delete:
                if st.button("Delete and Upload New SCORM Files"):
                    # Delete existing
                    st.warning(f"Deleting all contents under '{language_name}/'...")
                    for file_version_info, folder_name in bucket.ls(f"{language_name}/"):
                        bucket.delete_file_version(file_version_info.id_, file_version_info.file_name)
                    st.success(f"✅ All existing files under '{language_name}' deleted.")
        else:
            st.info(f"'{language_name}' does not exist. Ready to upload.")

        uploaded_files = st.file_uploader("Upload one or more SCORM ZIP files", type=["zip"], accept_multiple_files=True)

        if uploaded_files and st.button("Upload SCORM Files"):
            with st.spinner("Processing uploads..."):
                for uploaded in uploaded_files:
                    zip_name = os.path.splitext(uploaded.name)[0]
                    temp_dir = tempfile.mkdtemp()
                    zip_path = os.path.join(temp_dir, uploaded.name)
                    with open(zip_path, "wb") as f:
                        f.write(uploaded.read())
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(os.path.join(temp_dir, zip_name))

                    for root, _, files in os.walk(os.path.join(temp_dir, zip_name)):
                        for file in files:
                            local_path = os.path.join(root, file)
                            relative_path = os.path.relpath(local_path, os.path.join(temp_dir, zip_name)).replace("\\", "/")
                            b2_path = f"{language_name}/{zip_name}/{relative_path}"
                            bucket.upload_local_file(local_file=local_path, file_name=b2_path)
                    shutil.rmtree(temp_dir)
                st.success("✅ All SCORM files uploaded successfully.")

st.caption("Developed for instant SCORM review link generation and management.")
