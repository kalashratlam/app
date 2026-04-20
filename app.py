import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd

# ================= DATABASE CONNECTIVITY =================
# Aapki details maine yahan set kar di hain
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
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .overdue { border-left-color: #dc3545; }
    .upcoming { border-left-color: #28a745; }
    </style>
    """, unsafe_allow_html=True)

# ================= FUNCTIONS =================

def fetch_tasks():
    res = supabase.table("scheduler_tasks").select("*").order("task_time").execute()
    return res.data

def add_task_to_db(name, cat, dt, notes):
    supabase.table("scheduler_tasks").insert({
        "name": name,
        "category": cat,
        "task_time": dt.isoformat(),
        "notes": notes
    }).execute()

def archive_task_in_db(task_id):
    now_str = datetime.now().strftime("%d-%m %H:%M")
    supabase.table("scheduler_tasks").update({"is_archived": True, "archived_on": now_str}).eq("id", task_id).execute()

def restore_task_in_db(task_id):
    supabase.table("scheduler_tasks").update({"is_archived": False, "archived_on": None}).eq("id", task_id).execute()

# ================= APP UI =================

st.title("📱 Smart Scheduler PRO")

# Input Section
with st.expander("➕ Add New Task", expanded=False):
    with st.form("task_form", clear_on_submit=True):
        t_name = st.text_input("Task / Client Name")
        t_cat = st.selectbox("Category", ["Visit", "Pending Order", "Other"])
        col1, col2 = st.columns(2)
        t_date = col1.date_input("Date", datetime.now())
        t_time = col2.time_input("Time", (datetime.now() + timedelta(hours=1)).time())
        t_notes = st.text_area("Notes")
        
        if st.form_submit_button("Add Task"):
            if t_name:
                dt_combined = datetime.combine(t_date, t_time)
                add_task_to_db(t_name, t_cat, dt_combined, t_notes)
                st.success("Task Saved!")
                st.rerun()

# Dashboard
try:
    data = fetch_tasks()
    df = pd.DataFrame(data)
except:
    df = pd.DataFrame()

if not df.empty:
    df['task_time'] = pd.to_datetime(df['task_time'])
    # Ratlam time context ke liye current time
    now = datetime.now(df['task_time'].dt.tz)

    tab1, tab2 = st.tabs(["📋 Dashboard", "📦 Archive"])

    with tab1:
        cols = st.columns(3)
        cats = ["Visit", "Pending Order", "Other"]
        for i, cat in enumerate(cats):
            with cols[i]:
                st.subheader(cat)
                items = df[(df['category'] == cat) & (df['is_archived'] == False)]
                for _, row in items.iterrows():
                    is_overdue = row['task_time'] < now
                    s_class = "overdue" if is_overdue else "upcoming"
                    
                    st.markdown(f"""
                        <div class="task-card {s_class}">
                            <strong>{row['name']}</strong><br>
                            <small>⏰ {row['task_time'].strftime('%d-%m %H:%M')}</small>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button("Archive", key=f"id_{row['id']}"):
                        archive_task_in_db(row['id'])
                        st.rerun()

    with tab2:
        archived = df[df['is_archived'] == True]
        for _, row in archived.iterrows():
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"**{row['name']}** ({row['category']})")
            if col_b.button("Restore", key=f"res_{row['id']}"):
                restore_task_in_db(row['id'])
                st.rerun()
else:
    st.info("No tasks found.")
