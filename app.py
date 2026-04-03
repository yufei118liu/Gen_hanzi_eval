import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from pathlib import Path
import threading

# Cache the lock so it is shared across all user sessions
@st.cache_resource
def get_sync_lock():
    return threading.Lock()

sync_lock = get_sync_lock()

# --- CONFIGURATION ---
st.set_page_config(page_title="Model Evaluation", layout="wide")
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
conn = st.connection("gsheets", type=GSheetsConnection)
DATA_DIR = Path("samples")
SECTION_SIZE = 46  # 5 sections of 46 pairs = 230 total

# --- INITIALIZE SESSION STATE ---
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0
if "votes_buffer" not in st.session_state:
    st.session_state.votes_buffer = []
if "started" not in st.session_state:
    st.session_state.started = False
if "section_break" not in st.session_state:
    st.session_state.section_break = False
if "saved_and_exited" not in st.session_state:
    st.session_state.saved_and_exited = False

# --- DATA LOADING ---
if not DATA_DIR.exists():
    st.error(f"Folder '{DATA_DIR}' not found.")
    st.stop()

pair_folders = sorted([f for f in DATA_DIR.iterdir() if f.is_dir()],
                      key=lambda x: int(''.join(filter(str.isdigit, x.name)) or 0))
TOTAL_PAIRS = len(pair_folders)
TOTAL_SECTIONS = (TOTAL_PAIRS + SECTION_SIZE - 1) // SECTION_SIZE

# --- FUNCTIONS ---

def sync_to_sheets():
    if not st.session_state.votes_buffer:
        return

    try:
        # The lock ensures only one user can execute this block at a time
        with sync_lock: 
            df_new = pd.DataFrame(st.session_state.votes_buffer)
            existing_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
            updated_df = pd.concat([existing_df, df_new], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated_df)
            
        # Clear buffer AFTER successful sync
        st.session_state.votes_buffer = []
        st.sidebar.success("Synced successfully!")
    except Exception as e:
        st.sidebar.error(f"Sync delayed: {e}")
        

def handle_vote(pair_id, winner_filename):
    st.session_state.votes_buffer.append({
        "user_id": st.session_state.user_id,
        "pair_id": pair_id,
        "winner": winner_filename,
        "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    # Sync every 5 votes to minimize data loss
    if len(st.session_state.votes_buffer) >= 5:
        sync_to_sheets()

    st.session_state.current_idx += 1

    # Check if we hit a section boundary (but not the very end)
    if (st.session_state.current_idx % SECTION_SIZE == 0
            and st.session_state.current_idx < TOTAL_PAIRS):
        sync_to_sheets()
        st.session_state.section_break = True

def start_experiment():
    user_id = st.session_state.user_id_input.strip()
    if not user_id:
        return
    st.session_state.user_id = user_id

    # Check for existing votes to support resume
    try:
        existing_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
        user_votes = existing_df[existing_df["user_id"] == user_id]
        if not user_votes.empty:
            completed = user_votes["pair_id"].nunique()
            st.session_state.current_idx = completed
    except Exception:
        pass  # Fresh start if sheet is empty or unreadable

    st.session_state.started = True

def continue_section():
    st.session_state.section_break = False

def save_and_exit():
    sync_to_sheets()
    st.session_state.saved_and_exited = True
    st.session_state.section_break = False

# --- UI ---
if not st.session_state.started:
    st.title("Hanzi Generation Evaluation")
    st.markdown(f"""
    For each pair, pick the character that looks **more natural**, or choose **"Neither"**.
    The test has **{TOTAL_SECTIONS} sections** ({SECTION_SIZE} pairs each) — you can take breaks between sections.

    **Note on rendering:** Our renderings are imperfect. Please judge **structure and naturalness**, not rendering artifacts. Examples below:
    """)

    ex_col1, ex_col2, ex_col3, ex_col4 = st.columns(4)
    with ex_col1:
        st.caption("Perfect")
        st.image("perfect_example_1.png", width=180)
    with ex_col2:
        st.caption("Our rendering")
        st.image("rendered_example_1.png", width=180)
    with ex_col3:
        st.caption("Perfect")
        st.image("perfect_example_2.png", width=180)
    with ex_col4:
        st.caption("Our rendering")
        st.image("rendered_example_2.png", width=180)

    st.divider()

    st.text_input("Enter your User ID to start (or re-enter to resume):", key="user_id_input")
    st.caption("Remember this ID — you'll need it to resume after a break.")

    if st.session_state.get("user_id_input", "").strip():
        st.button("Start Experiment", on_click=start_experiment, type="primary", use_container_width=True)
    else:
        st.button("Start Experiment", type="primary", use_container_width=True, disabled=True)

elif st.session_state.saved_and_exited:
    st.title("Progress Saved!")
    st.success(f"Your progress has been saved. You have completed {st.session_state.current_idx} of {TOTAL_PAIRS} pairs.")
    st.info(f"Your User ID is: **{st.session_state.user_id}**\n\nPlease remember this ID. When you are ready to continue, come back and enter the same ID to resume.")

elif st.session_state.section_break:
    current_section = st.session_state.current_idx // SECTION_SIZE
    st.title(f"Section {current_section} of {TOTAL_SECTIONS} Complete!")
    st.success(f"You have completed {st.session_state.current_idx} of {TOTAL_PAIRS} pairs.")
    st.markdown("You can continue to the next section, or save your progress and come back later.")

    col1, col2 = st.columns(2)
    with col1:
        st.button("Continue to Next Section", on_click=continue_section, type="primary", use_container_width=True)
    with col2:
        st.button("Save & Exit", on_click=save_and_exit, use_container_width=True)

elif st.session_state.current_idx < TOTAL_PAIRS:
    current_folder = pair_folders[st.session_state.current_idx]
    pair_id = current_folder.name
    images = sorted([img for img in current_folder.iterdir() if img.suffix.lower() in [".png", ".jpg", ".jpeg"]])

    if len(images) < 2:
        st.session_state.current_idx += 1
        st.rerun()

    current_section = st.session_state.current_idx // SECTION_SIZE + 1
    idx_in_section = st.session_state.current_idx % SECTION_SIZE + 1
    st.title(f"Section {current_section}/{TOTAL_SECTIONS} — Pair {idx_in_section} of {SECTION_SIZE}")

    col1, col2 = st.columns(2)
    with col1:
        st.image(str(images[0]), width=400)
        st.button("Choose Option A", key=f"a_{pair_id}", on_click=handle_vote, args=(pair_id, images[0].name), use_container_width=True)

    with col2:
        st.image(str(images[1]), width=400)
        st.button("Choose Option B", key=f"b_{pair_id}", on_click=handle_vote, args=(pair_id, images[1].name), use_container_width=True)

    st.write("")
    st.button("Neither looks likely", key=f"neither_{pair_id}", on_click=handle_vote, args=(pair_id, "Neither"), use_container_width=True)

    st.progress(st.session_state.current_idx / TOTAL_PAIRS)

    if st.session_state.votes_buffer:
        st.sidebar.write(f"{len(st.session_state.votes_buffer)} votes waiting to sync...")

else:
    with st.spinner("Saving your final results..."):
        sync_to_sheets()
    st.success("All evaluations complete! Thank you.")
    st.balloons()
