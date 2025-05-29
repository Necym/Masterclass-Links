import streamlit as st
import os
import zipfile
import shutil
import tempfile
import urllib.parse
import hashlib
import requests

# ─── Backblaze B2 Credentials ───
B2_KEY_ID   = "0057d19983190740000000003"
B2_APP_KEY  = "K005tH7/zOTPfBmFlyDMy2cYamvw5y8"
BUCKET_NAME = "filesfornecym"
BASE_URL    = f"https://f005.backblazeb2.com/file/{BUCKET_NAME}"
API_VER     = "v2"

# ─── Helper: Authorize & Cache for 1h ───
@st.cache_data(ttl=3600)
def authorize_b2():
    resp = requests.get(
        f"https://api.backblazeb2.com/b2api/{API_VER}/b2_authorize_account",
        auth=(B2_KEY_ID, B2_APP_KEY)
    )
    resp.raise_for_status()
    return resp.json()

auth = authorize_b2()
API_URL      = auth["apiUrl"]
AUTH_TOKEN   = auth["authorizationToken"]
ACCOUNT_ID   = auth["accountId"]

# ─── Helper: Find your bucketId ───
@st.cache_data(ttl=3600)
def get_bucket_id():
    payload = {"accountId": ACCOUNT_ID}
    resp = requests.post(
        f"{API_URL}/b2api/{API_VER}/b2_list_buckets",
        headers={"Authorization": AUTH_TOKEN},
        json=payload
    )
    resp.raise_for_status()
    for b in resp.json()["buckets"]:
        if b["bucketName"] == BUCKET_NAME:
            return b["bucketId"]
    raise RuntimeError(f"Bucket {BUCKET_NAME!r} not found")

BUCKET_ID = get_bucket_id()

# ─── B2 Operations ───
def list_files(prefix=""):
    payload = {
        "bucketId": BUCKET_ID,
        "prefix": prefix,
        "maxFileCount": 10000
    }
    resp = requests.post(
        f"{API_URL}/b2api/{API_VER}/b2_list_file_names",
        headers={"Authorization": AUTH_TOKEN},
        json=payload
    )
    resp.raise_for_status()
    return resp.json()["files"]  # each: {fileName, fileId, ...}

def delete_file_version(file_name, file_id):
    payload = {"fileName": file_name, "fileId": file_id}
    resp = requests.post(
        f"{API_URL}/b2api/{API_VER}/b2_delete_file_version",
        headers={"Authorization": AUTH_TOKEN},
        json=payload
    )
    resp.raise_for_status()

def get_upload_url():
    payload = {"bucketId": BUCKET_ID}
    resp = requests.post(
        f"{API_URL}/b2api/{API_VER}/b2_get_upload_url",
        headers={"Authorization": AUTH_TOKEN},
        json=payload
    )
    resp.raise_for_status()
    j = resp.json()
    return j["uploadUrl"], j["authorizationToken"]

def upload_file(local_path, b2_path):
    upload_url, upload_token = get_upload_url()
    with open(local_path, "rb") as f:
        data = f.read()
    sha1 = hashlib.sha1(data).hexdigest()
    headers = {
        "Authorization": upload_token,
        "X-Bz-File-Name": urllib.parse.quote(b2_path, safe=""),
        "Content-Type": "b2/x-auto",
        "X-Bz-Content-Sha1": sha1
    }
    resp = requests.post(upload_url, headers=headers, data=data)
    resp.raise_for_status()

# ─── Streamlit UI ───
st.set_page_config(page_title="SCORM Review Links")
st.title("SCORM Review Link Generator")

mode = st.sidebar.radio("Mode", ["View Links", "Upload New Language"])

if mode == "View Links":
    # gather all file names
    files = list_files("")
    langs = {f["fileName"].split("/",1)[0] for f in files if "/" in f["fileName"]}
    sel = st.selectbox("Select Language:", sorted(langs))

    if sel:
        sub = {
            fn.split("/")[1]
            for fn in (f["fileName"] for f in files)
            if fn.startswith(f"{sel}/") and fn.count("/") >= 2
        }
        if sub:
            st.subheader(f"SCORM Packages in {sel}:")
            for pkg in sorted(sub):
                safe = pkg.replace("[","\\[").replace("]","\\]")
                link = f"{BASE_URL}/{urllib.parse.quote(sel)}/{urllib.parse.quote(pkg)}/story.html"
                st.markdown(f"📄 [{safe}]({link})")
        else:
            st.info("No SCORM packages found.")

elif mode == "Upload New Language":
    langs = {f["fileName"].split("/",1)[0] for f in list_files("") if "/" in f["fileName"]}
    new_lang = st.text_input("Language folder name (e.g. German):")

    if new_lang:
        if new_lang in langs:
            if st.checkbox(f"⚠️ Delete existing '{new_lang}/' first"):
                if st.button("Delete & Start Upload"):
                    with st.spinner("Deleting…"):
                        for f in list_files(f"{new_lang}/"):
                            delete_file_version(f["fileName"], f["fileId"])
                    st.success("✅ Deleted old files.")
        else:
            st.info(f"'{new_lang}' is new; ready to upload.")

        uploads = st.file_uploader("SCORM ZIPs", type="zip", accept_multiple_files=True)
        if uploads and st.button("Start Upload"):
            with st.spinner("Uploading…"):
                for z in uploads:
                    base = os.path.splitext(z.name)[0]
                    tmp = tempfile.mkdtemp()
                    path = os.path.join(tmp, z.name)
                    with open(path,"wb") as f: f.write(z.read())
                    ext = os.path.join(tmp, base)
                    os.makedirs(ext, exist_ok=True)
                    with zipfile.ZipFile(path) as zp:
                        zp.extractall(ext)
                    for root,_,fs in os.walk(ext):
                        for fn in fs:
                            lp = os.path.join(root, fn)
                            rel = os.path.relpath(lp, ext).replace("\\","/")
                            b2p = f"{new_lang}/{base}/{rel}"
                            upload_file(lp, b2p)
                    shutil.rmtree(tmp)
                st.success("✅ Upload complete.")

st.caption("Developed for instant SCORM review link generation and management.")
