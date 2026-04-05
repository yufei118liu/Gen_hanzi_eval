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

# --- INITIALIZE SESSION STATE ---
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0
if "votes_buffer" not in st.session_state:
    st.session_state.votes_buffer = []
if "started" not in st.session_state:
    st.session_state.started = False
if "saved_and_exited" not in st.session_state:
    st.session_state.saved_and_exited = False

# --- DATA LOADING ---
if not DATA_DIR.exists():
    st.error(f"Folder '{DATA_DIR}' not found.")
    st.stop()

pair_folders = sorted([f for f in DATA_DIR.iterdir() if f.is_dir()],
                      key=lambda x: int(''.join(filter(str.isdigit, x.name)) or 0))
TOTAL_PAIRS = len(pair_folders)

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

    st.session_state.current_idx += 1

    # Sync every 5 votes to minimize data loss
    if len(st.session_state.votes_buffer) >= 5:
        sync_to_sheets()

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

def save_and_exit():
    sync_to_sheets()
    st.session_state.saved_and_exited = True

# --- UI ---
if not st.session_state.started:
    st.title("Hanzi Generation Evaluation")
    st.markdown(f"""
    For each pair, pick the character that looks **more natural**, or choose **"Neither"**.
    The test has **{TOTAL_PAIRS} pairs** — you can save your progress and come back anytime.

    **Note on rendering:** Our renderings are imperfect. Please judge **structure and naturalness**, not rendering artifacts. Examples below:
    """)
    st.markdown(f"""
    对于每一对字符，请选择**看起来更自然**的那个，或选择**"两者都不像"**。
    测试共有 **{TOTAL_PAIRS} 对** — 您可以随时保存进度，稍后继续。

    **关于渲染的说明：** 我们的渲染并不完美。请根据**结构和自然度**进行判断，忽略渲染瑕疵。示例如下：
    """)

    ex_col1, ex_col2, ex_col3, ex_col4 = st.columns(4)
    with ex_col1:
        st.caption("Perfect / 标准")
        st.image("perfect_example_1.png", width=180)
    with ex_col2:
        st.caption("Our rendering / 我们的渲染")
        st.image("rendered_example_1.png", width=180)
    with ex_col3:
        st.caption("Perfect / 标准")
        st.image("perfect_example_2.png", width=180)
    with ex_col4:
        st.caption("Our rendering / 我们的渲染")
        st.image("rendered_example_2.png", width=180)

    st.divider()

    st.text_input("Enter your User ID to start (or re-enter to resume):", key="user_id_input")
    st.caption("Remember this ID — you'll need it to resume after a break.")
    st.caption("请记住此 ID — 休息后继续时需要用到它。")

    if st.session_state.get("user_id_input", "").strip():
        st.button("Start Experiment", on_click=start_experiment, type="primary", use_container_width=True)
    else:
        st.button("Start Experiment", type="primary", use_container_width=True, disabled=True)

elif st.session_state.saved_and_exited:
    st.title("Progress Saved!")
    st.success(f"Your progress has been saved. You have completed {st.session_state.current_idx} of {TOTAL_PAIRS} pairs.")
    st.info(f"Your User ID is: **{st.session_state.user_id}**\n\nPlease remember this ID. When you are ready to continue, come back and enter the same ID to resume.")
    st.markdown("---")
    st.markdown(f"**进度已保存！** 您已完成 {st.session_state.current_idx} / {TOTAL_PAIRS} 对。")
    st.info(f"您的用户 ID 是：**{st.session_state.user_id}**\n\n请记住此 ID。准备好继续时，重新打开页面并输入相同的 ID 即可恢复进度。")

elif st.session_state.current_idx < TOTAL_PAIRS:
    current_folder = pair_folders[st.session_state.current_idx]
    pair_id = current_folder.name
    images = sorted([img for img in current_folder.iterdir() if img.suffix.lower() in [".png", ".jpg", ".jpeg"]])

    if len(images) < 2:
        st.session_state.current_idx += 1
        st.rerun()

    st.title(f"Pair {st.session_state.current_idx + 1} of {TOTAL_PAIRS}")

    col1, col2 = st.columns(2)
    with col1:
        st.image(str(images[0]), width=400)
        st.button("Choose Option A / 选择 A", key=f"a_{pair_id}", on_click=handle_vote, args=(pair_id, images[0].name), use_container_width=True)

    with col2:
        st.image(str(images[1]), width=400)
        st.button("Choose Option B / 选择 B", key=f"b_{pair_id}", on_click=handle_vote, args=(pair_id, images[1].name), use_container_width=True)

    st.write("")
    st.button("Neither looks likely / 两者都不像", key=f"neither_{pair_id}", on_click=handle_vote, args=(pair_id, "Neither"), use_container_width=True)

    st.progress(st.session_state.current_idx / TOTAL_PAIRS)

    st.sidebar.button("Save & Exit / 保存并退出", on_click=save_and_exit, use_container_width=True)
    if st.session_state.votes_buffer:
        st.sidebar.write(f"{len(st.session_state.votes_buffer)} votes waiting to sync...")

else:
    with st.spinner("Saving your final results..."):
        sync_to_sheets()
    st.success("All evaluations complete! Thank you.")
    st.success("所有评估已完成！谢谢您的参与。")
    st.balloons()
