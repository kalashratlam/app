import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd

# ================= DATABASE CONNECTIVITY =================
SUPABASE_URL = "https://knjfotknwxlrjscuyoir.supabase.co"
SUPABASE_KEY = "sb_publishable_wwT5nUUkokrcwVod12R6TQ_fy57CDZA"

@st.cache_resource
def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

# ================= UI CONFIGURATION =================
st.set_page_config(page_title="Smart Scheduler PRO", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .task-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .overdue { border-left-color: #dc3545; }
    .upcoming { border-left-color: #28a745; }
    .stButton>button { width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# ================= SESSION STATE (For Editing) =================
if 'editing_task' not in st.session_state:
    st.session_state.editing_task = None

# ================= LOGIC FUNCTIONS =================

def fetch_tasks():
    try:
        res = supabase.table("scheduler_tasks").select("*").order("task_time").execute()
        return res.data
    except: return []

def save_task(name, cat, dt, notes, task_id=None):
    data = {
        "name": str(name),
        "category": str(cat),
        "task_time": dt.isoformat(),
        "notes": str(notes) if notes else "",
        "is_archived": False
    }
    try:
        if task_id:
            supabase.table("scheduler_tasks").update(data).eq("id", task_id).execute()
        else:
            supabase.table("scheduler_tasks").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# ================= APP UI =================

st.title("📱 Smart Scheduler PRO")

# --- Input/Edit Form ---
# Agar koi task edit ho raha hai, toh form expanded khulega
is_editing = st.session_state.editing_task is not None
with st.expander("📝 " + ("Edit Task" if is_editing else "Add New Task"), expanded=is_editing):
    with st.form("main_form", clear_on_submit=not is_editing):
        # Default values set karna agar edit mode hai
        d_name = st.session_state.editing_task['name'] if is_editing else ""
        d_cat = st.session_state.editing_task['category'] if is_editing else "Visit"
        d_notes = st.session_state.editing_task['notes'] if is_editing else ""
        # Time parsing for edit
        if is_editing:
            dt_obj = pd.to_datetime(st.session_state.editing_task['task_time'])
            d_date = dt_obj.date()
            d_time = dt_obj.time()
        else:
            d_date = datetime.now()
            d_time = (datetime.now() + timedelta(hours=1)).time()

        t_name = st.text_input("Task / Client Name", value=d_name)
        t_cat = st.selectbox("Category", ["Visit", "Pending Order", "Other"], index=["Visit", "Pending Order", "Other"].index(d_cat))
        col1, col2 = st.columns(2)
        t_date = col1.date_input("Date", d_date)
        t_time = col2.time_input("Time", d_time)
        t_notes = st.text_area("Notes", value=d_notes)
        
        btn_label = "Update Task" if is_editing else "Add Task"
        if st.form_submit_button(btn_label):
            dt_combined = datetime.combine(t_date, t_time)
            tid = st.session_state.editing_task['id'] if is_editing else None
            if save_task(t_name, t_cat, dt_combined, t_notes, tid):
                st.session_state.editing_task = None # Reset edit mode
                st.success("Success!")
                st.rerun()

    if is_editing:
        if st.button("Cancel Edit"):
            st.session_state.editing_task = None
            st.rerun()

# --- Load & Display Data ---
data = fetch_tasks()
df = pd.DataFrame(data)

if not df.empty:
    df['task_time'] = pd.to_datetime(df['task_time'])
    now = datetime.now(df['task_time'].dt.tz)
    tab1, tab2 = st.tabs(["📋 Dashboard", "📦 Archive"])

    with tab1:
        cols = st.columns(3)
        cats = ["Visit", "Pending Order", "Other"]
        for i, cat in enumerate(cats):
            with cols[i]:
                st.subheader(cat)
                active = df[(df['category'] == cat) & (df['is_archived'] == False)]
                for _, row in active.iterrows():
                    is_overdue = row['task_time'] < now
                    s_class = "overdue" if is_overdue else "upcoming"
                    
                    st.markdown(f"""<div class="task-card {s_class}">
                        <strong>{row['name']}</strong><br>
                        <small>⏰ {row['task_time'].strftime('%d %b, %I:%M %p')}</small><br>
                        <small style="font-style: italic;">{row['notes'] if row['notes'] else ''}</small>
                    </div>""", unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    if c1.button("Edit", key=f"edit_{row['id']}"):
                        st.session_state.editing_task = row.to_dict()
                        st.rerun()
                    if c2.button("Done", key=f"done_{row['id']}"):
                        supabase.table("scheduler_tasks").update({"is_archived": True, "archived_on": datetime.now().strftime("%d-%m %H:%M")}).eq("id", row['id']).execute()
                        st.rerun()
                    st.write("---")

    with tab2:
        archived = df[df['is_archived'] == True]
        for _, row in archived.iterrows():
            with st.container(border=True):
                st.write(f"**{row['name']}** ({row['category']})")
                if st.button("Restore", key=f"res_{row['id']}"):
                    supabase.table("scheduler_tasks").update({"is_archived": False, "archived_on": None}).eq("id", row['id']).execute()
                    st.rerun()
else:
    st.info("No tasks yet.")
