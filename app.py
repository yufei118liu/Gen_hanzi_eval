import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from pathlib import Path
import uuid

# --- CONFIGURATION ---
st.set_page_config(page_title="Model Evaluation", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

DATA_DIR = Path("sample") 

# --- INITIALIZE SESSION STATE ---
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0

# --- DATA LOADING ---
if not DATA_DIR.exists():
    st.error(f"Folder '{DATA_DIR}' not found. Check your GitHub repository.")
    st.stop()

# Get folders and sort them
pair_folders = sorted([f for f in DATA_DIR.iterdir() if f.is_dir()], 
                      key=lambda x: int(''.join(filter(str.isdigit, x.name)) or 0))
TOTAL_PAIRS = len(pair_folders)

# --- THE LOGIC ---
def handle_vote(pair_id, winner_filename):
    # 1. Prepare data
    new_data = {
        "user_id": [st.session_state.user_id],
        "pair_id": [pair_id],
        "winner": [winner_filename],
        "timestamp": [pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")]
    }
    df_new = pd.DataFrame(new_data)

    # 2. Update Google Sheets
    try:
        # Read existing data to append to it
        existing_df = conn.read(worksheet="Sheet1")
        updated_df = pd.concat([existing_df, df_new], ignore_index=True)
        conn.update(worksheet="Sheet1", data=updated_df)
    except Exception as e:
        # Even if sheets fail, we show this in the sidebar so the user can continue
        st.sidebar.error(f"Save failed: {e}")

    # 3. MOVE TO NEXT IMAGE (This makes the button "work" visually)
    st.session_state.current_idx += 1

# --- UI ---
if st.session_state.current_idx < TOTAL_PAIRS:
    current_folder = pair_folders[st.session_state.current_idx]
    pair_id = current_folder.name
    
    # Grab images (support png, jpg, jpeg)
    images = sorted([img for img in current_folder.iterdir() if img.suffix.lower() in [".png", ".jpg", ".jpeg"]])
    
    if len(images) < 2:
        st.session_state.current_idx += 1
        st.rerun()

    st.title(f"Pair {st.session_state.current_idx + 1} of {TOTAL_PAIRS}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.image(str(images[0]), use_container_width=True)
        # We use a callback (on_click) for faster response
        st.button("Option A", key=f"a_{pair_id}", use_container_width=True, 
                  on_click=handle_vote, args=(pair_id, images[0].name))

    with col2:
        st.image(str(images[1]), use_container_width=True)
        st.button("Option B", key=f"b_{pair_id}", use_container_width=True, 
                  on_click=handle_vote, args=(pair_id, images[1].name))
            
    st.progress((st.session_state.current_idx) / TOTAL_PAIRS)
else:
    st.success("🎉 All evaluations complete! Thank you.")
    st.balloons()