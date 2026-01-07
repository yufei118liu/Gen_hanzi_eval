import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from pathlib import Path
import random

# --- CONFIGURATION ---
ST_CONN = st.connection("gsheets", type=GSheetsConnection)
DATA_DIR = Path("sample")
# Get all subfolders and sort them naturally (1, 2, 10 instead of 1, 10, 2)
pair_folders = sorted([f for f in DATA_DIR.iterdir() if f.is_dir()], 
                      key=lambda x: int(''.join(filter(str.isdigit, x.name)) or 0))
TOTAL_PAIRS = len(pair_folders)

st.set_page_config(page_title="Model Evaluation", layout="wide")

# --- SESSION STATE ---
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0  # Start at first folder
if "user_id" not in st.session_state:
    st.session_state.user_id = st.text_input("Enter your Participant ID to start:", "").strip()

# --- FUNCTIONS ---
def save_vote(pair_id, winner_name):
    new_row = pd.DataFrame([{
        "user_id": st.session_state.user_id,
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
        st.error(f"Error saving data: {e}. Please check your internet or spreadsheet permissions.")

# --- UI LAYOUT ---
if not st.session_state.user_id:
    st.warning("Please enter your Participant ID to begin.")
    st.stop()

if st.session_state.current_idx < TOTAL_PAIRS:
    current_folder = pair_folders[st.session_state.current_idx]
    pair_id = current_folder.name
    
    # Grab images (finds first two images regardless of filename)
    images = sorted([img for img in current_folder.iterdir() if img.suffix.lower() in [".png", ".jpg", ".jpeg"]])
    
    if len(images) < 2:
        st.error(f"Folder {pair_id} does not have 2 images. Skipping...")
        st.session_state.current_idx += 1
        st.rerun()

    # RANDOMIZE left/right to prevent bias
    display_order = [0, 1]
    # random.shuffle(display_order) # Uncomment this if you want to flip A/B randomly

    st.title(f"Evaluation: {st.session_state.current_idx + 1} / {TOTAL_PAIRS}")
    st.write(f"Pair ID: `{pair_id}`")

    col1, col2 = st.columns(2)
    
    with col1:
        idx1 = display_order[0]
        st.image(str(images[idx1]), use_container_width=True, caption="Option 1")
        if st.button(f"Option 1 is better", key=f"btn_1_{pair_id}", use_container_width=True):
            save_vote(pair_id, images[idx1].name)
            st.rerun()

    with col2:
        idx2 = display_order[1]
        st.image(str(images[idx2]), use_container_width=True, caption="Option 2")
        if st.button(f"Option 2 is better", key=f"btn_2_{pair_id}", use_container_width=True):
            save_vote(pair_id, images[idx2].name)
            st.rerun()
            
    st.progress((st.session_state.current_idx + 1) / TOTAL_PAIRS)

else:
    st.success("🎉 All done! Thank you for your time.")
    st.balloons()