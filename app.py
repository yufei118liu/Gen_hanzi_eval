import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from pathlib import Path
import uuid

# --- CONFIGURATION ---
st.set_page_config(page_title="Model Evaluation", layout="wide")
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
conn = st.connection("gsheets", type=GSheetsConnection)
DATA_DIR = Path("samples") 

# --- INITIALIZE SESSION STATE ---
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0
if "votes_buffer" not in st.session_state:
    st.session_state.votes_buffer = [] # Temporary storage to avoid hitting Google API limits

# --- DATA LOADING ---
if not DATA_DIR.exists():
    st.error(f"Folder '{DATA_DIR}' not found.")
    st.stop()

pair_folders = sorted([f for f in DATA_DIR.iterdir() if f.is_dir()], 
                      key=lambda x: int(''.join(filter(str.isdigit, x.name)) or 0))
TOTAL_PAIRS = len(pair_folders)

# --- FUNCTIONS ---
def sync_to_sheets():
    """Writes all buffered votes to Google Sheets in one single call"""
    if not st.session_state.votes_buffer:
        return
        
    try:
        # 1. Prepare the new data
        df_new = pd.DataFrame(st.session_state.votes_buffer)
        
        # 2. Read existing data and append
        existing_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1")
        updated_df = pd.concat([existing_df, df_new], ignore_index=True)
        
        # 3. Write back to Google (Only 1 API call here)
        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated_df)
        
        # 4. Clear the buffer if successful
        st.session_state.votes_buffer = []
    except Exception as e:
        st.sidebar.error(f"Sync delayed: {e}")

def handle_vote(pair_id, winner_filename):
    # Add vote to buffer
    st.session_state.votes_buffer.append({
        "user_id": st.session_state.user_id,
        "pair_id": pair_id,
        "winner": winner_filename,
        "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Sync to Google Sheets every 5 votes to stay under the 429 limit
    if len(st.session_state.votes_buffer) >= 5:
        sync_to_sheets()

    # Move to next image immediately
    st.session_state.current_idx += 1

# --- UI ---
if st.session_state.current_idx < TOTAL_PAIRS:
    current_folder = pair_folders[st.session_state.current_idx]
    pair_id = current_folder.name
    images = sorted([img for img in current_folder.iterdir() if img.suffix.lower() in [".png", ".jpg", ".jpeg"]])
    
    if len(images) < 2:
        st.session_state.current_idx += 1
        st.rerun()

    st.title(f"Pair {st.session_state.current_idx + 1} of {TOTAL_PAIRS}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.image(str(images[0]), width=400) # Fixed width
        st.button("Option A", key=f"a_{pair_id}", width=400, on_click=handle_vote, args=(pair_id, images[0].name))

    with col2:
        st.image(str(images[1]), width=400) # Fixed width
        st.button("Option B", key=f"b_{pair_id}", width=400, on_click=handle_vote, args=(pair_id, images[1].name))
            
    st.progress((st.session_state.current_idx) / TOTAL_PAIRS)
    
    # Show status in sidebar
    if st.session_state.votes_buffer:
        st.sidebar.write(f"🗳️ {len(st.session_state.votes_buffer)} votes waiting to sync...")

else:
    # IMPORTANT: Final sync when the user finishes
    with st.spinner("Saving your final results..."):
        sync_to_sheets()
    st.success("🎉 All evaluations complete! Thank you.")
    st.balloons()