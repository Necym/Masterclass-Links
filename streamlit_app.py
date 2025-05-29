import streamlit as st
import os
import zipfile
import shutil
import tempfile
import urllib.parse
from b2sdk.v2 import InMemoryAccountInfo, B2Api

# ─── Backblaze B2 Credentials ───
B2_KEY_ID = "0057d19983190740000000003"
B2_APP_KEY = "K005tH7/zOTPfBmFlyDMy2cYamvw5y8"
BUCKET_NAME = "filesfornecym"
BASE_URL = f"https://f005.backblazeb2.com/file/{BUCKET_NAME}"

# ─── Connect to Backblaze B2 ───
info = InMemoryAccountInfo()
b2_api = B2Api(info)

try:
    b2_api.authorize_account("production", B2_KEY_ID, B2_APP_KEY)
    buckets = b2_api.list_buckets()
    bucket = next(b for b in buckets if b.name == BUCKET_NAME)
    st.success("✅ Connected to Backblaze B2.")
except Exception as e:
    st.error(f"❌ Failed to connect to Backblaze B2: {e}")
    st.stop()

# ─── Streamlit Setup ───
st.set_page_config(page_title="SCORM Review Links")
st.title("SCORM Review Link Generator")

mode = st.sidebar.radio("Choose Mode", ["View Links", "Upload New Language"])

# ─── View Mode ───
if mode == "View Links":
    language_folders = set()
    all_files = []
    for entry in b2_api.list_file_names(bucket.id_):
        file_name = entry.file_name
        all_files.append((entry, file_name))
        if file_name:
            language = file_name.strip('/').split('/')[0]
            language_folders.add(language)

    sorted_languages = sorted(language_folders)
    selected_language = st.selectbox("Select Language:", sorted_languages)

    if selected_language:
        subfolders = set()
        filtered_files = [f for f in all_files if f[1].startswith(f"{selected_language}/")]
        for file_version_info, file_name in filtered_files:
            parts = file_name.strip('/').split('/')
            if len(parts) >= 2:
                subfolders.add(parts[1])

        sorted_scorms = sorted(subfolders)

        if sorted_scorms:
            st.subheader(f"SCORM Packages in {selected_language}:")
            for scorm_folder in sorted_scorms:
                safe_display = scorm_folder.replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('\\', '\\\\')
                encoded_lang = urllib.parse.quote(selected_language)
                encoded_folder = urllib.parse.quote(scorm_folder)
                review_link = f"{BASE_URL}/{encoded_lang}/{encoded_folder}/story.html"
                st.markdown(f"📄 [{safe_display}]({review_link})", unsafe_allow_html=False)
        else:
            st.info(f"No SCORM courses found under '{selected_language}'.")

# ─── Upload Mode ───
elif mode == "Upload New Language":
    language_name = st.text_input("Enter new language folder name (e.g., German)")

    if language_name:
        all_files = []
        existing_languages = set()
        for entry in b2_api.list_file_names(bucket.id_):
            file_name = entry.file_name
            all_files.append((entry, file_name))
            if file_name:
                existing_languages.add(file_name.strip('/').split('/')[0])

        if language_name in existing_languages:
            confirm_delete = st.checkbox(f"⚠️ '{language_name}' already exists. Check to confirm deletion of all contents.")
            if confirm_delete and st.button("Delete and Upload New SCORM Files"):
                st.warning(f"Deleting all files under '{language_name}/'...")
                for entry, file_name in all_files:
                    if file_name.startswith(f"{language_name}/"):
                        bucket.delete_file_version(entry.id_, file_name)
                st.success(f"✅ All existing files under '{language_name}' deleted.")
        else:
            st.info(f"'{language_name}' does not exist yet. Ready to upload.")

        uploaded_files = st.file_uploader("Upload SCORM ZIP files", type=["zip"], accept_multiple_files=True)

        if uploaded_files and st.button("Upload SCORM Files"):
            with st.spinner("Processing uploads..."):
                for uploaded in uploaded_files:
                    zip_name = os.path.splitext(uploaded.name)[0]
                    temp_dir = tempfile.mkdtemp()
                    zip_path = os.path.join(temp_dir, uploaded.name)

                    with open(zip_path, "wb") as f:
                        f.write(uploaded.read())

                    extract_path = os.path.join(temp_dir, zip_name)
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_path)

                    for root, _, files in os.walk(extract_path):
                        for file in files:
                            local_path = os.path.join(root, file)
                            relative_path = os.path.relpath(local_path, extract_path).replace("\\", "/")
                            b2_path = f"{language_name}/{zip_name}/{relative_path}"
                            bucket.upload_local_file(local_file=local_path, file_name=b2_path)

                    shutil.rmtree(temp_dir)

                st.success("✅ SCORM files uploaded successfully.")

st.caption("Developed for instant SCORM review link generation and management.")
