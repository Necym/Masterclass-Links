# 📦 Streamlit App: Search Language ➔ Show SCORM Review Links

import streamlit as st
import os
from b2sdk.v2 import InMemoryAccountInfo, B2Api

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
st.set_page_config(page_title="SCORM Review Links", page_icon="📍")
st.title("\ud83d\udccd SCORM Review Link Generator")

# ─── Step 1: Detect available languages ───

# List all folders (prefixes)
all_files = bucket.ls('', show_versions=False)
language_folders = set()

for file_version_info, folder_name in all_files:
    if folder_name is not None:
        language = folder_name.strip('/').split('/')[0]
        language_folders.add(language)

sorted_languages = sorted(list(language_folders))

# ─── Step 2: Select Language ───
selected_language = st.selectbox("Select Language:", sorted_languages)

if selected_language:
    # ─── Step 3: Find SCORM folders inside selected language ───
    subfolders = set()
    all_files = bucket.ls(f"{selected_language}/", show_versions=False)

    for file_version_info, folder_name in all_files:
        if folder_name is not None:
            parts = folder_name.strip('/').split('/')
            if len(parts) >= 2:
                subfolders.add(parts[1])

    sorted_scorms = sorted(list(subfolders))

    if sorted_scorms:
        st.subheader(f"SCORM Packages in {selected_language}:")

        for scorm_folder in sorted_scorms:
            review_link = f"{BASE_URL}/{selected_language}/{scorm_folder}/story.html"
            st.markdown(f"\ud83d\udd17 [{scorm_folder}]({review_link})")
    else:
        st.info(f"No SCORM courses found inside {selected_language}.")

st.caption("Developed for instant SCORM review link generation \ud83d\ude80")
