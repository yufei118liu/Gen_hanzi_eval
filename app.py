import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from pathlib import Path
import uuid  # Used to generate a unique ID automatically

# --- CONFIGURATION ---
ST_CONN = st.connection("gsheets", type=GSheetsConnection)
DATA_DIR = Path("samples") # Ensure this matches your GitHub folder name (case-sensitive)

# --- SESSION STATE INITIALIZATION ---
# 1. Generate a random User ID if it doesn't exist yet
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8] # Generates a short 8-char ID like 'a1b2c3d4'

if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0

# --- DATA LOADING ---
if not DATA_DIR.exists():
    st.error(f"Folder '{DATA_DIR}' not found. Check your GitHub repository.")
    st.stop()

pair_folders = sorted([f for f in DATA_DIR.iterdir() if f.is_dir()], 
                      key=lambda x: int(''.join(filter(str.isdigit, x.name)) or 0))
TOTAL_PAIRS = len(pair_folders)

# --- FUNCTIONS ---
def save_vote(pair_id, winner_name):
    new_row = pd.DataFrame([{
        "user_id": st.session_state.user_id, # This is now the automatic ID
        "pair_id": pair_id,
        "winner": winner_name,
        "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    
    try:
        existing_data = ST_CONN.read(worksheet="Sheet1")
        updated_data = pd.concat([existing_data, new_row], ignore_index=True)
        ST_CONN.update(worksheet="Sheet1", data=updated_data)
        st.session_state.current_idx += 1
    except Exception as e:
        st.error("Connection error. Your vote might not have been saved.")

# --- UI LAYOUT ---
if st.session_state.current_idx < TOTAL_PAIRS:
    current_folder = pair_folders[st.session_state.current_idx]
    pair_id = current_folder.name
    
    # Grab images
    images = sorted([img for img in current_folder.iterdir() if img.suffix.lower() in [".png", ".jpg", ".jpeg"]])
    
    if len(images) < 2:
        st.session_state.current_idx += 1
        st.rerun()

    st.title(f"Image Evaluation: {st.session_state.current_idx + 1} / {TOTAL_PAIRS}")
    st.write("Click the button under the image you prefer.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.image(str(images[0]), use_container_width=True)
        if st.button(f"Option A", key=f"btn_a_{pair_id}", use_container_width=True):
            save_vote(pair_id, images[0].name)
            st.rerun()

    with col2:
        st.image(str(images[1]), use_container_width=True)
        if st.button(f"Option B", key=f"btn_b_{pair_id}", use_container_width=True):
            save_vote(pair_id, images[1].name)
            st.rerun()
            
    st.progress((st.session_state.current_idx + 1) / TOTAL_PAIRS)
    st.caption(f"Your Session ID: {st.session_state.user_id}")

else:
    st.success("🎉 Thank you! You've completed the evaluation.")
    st.balloons()