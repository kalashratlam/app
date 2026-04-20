import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd

# ================= DATABASE CONNECTIVITY =================
# Aapki details yahan pre-filled hain
SUPABASE_URL = "https://knjfotknwxlrjscuyoir.supabase.co"
SUPABASE_KEY = "sb_publishable_wwT5nUUkokrcwVod12R6TQ_fy57CDZA"

@st.cache_resource
def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

# ================= UI CONFIGURATION =================
st.set_page_config(page_title="Smart Scheduler PRO", layout="wide")

# Custom CSS for modern card look
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .task-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .overdue { border-left-color: #dc3545; }
    .upcoming { border-left-color: #28a745; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ================= LOGIC FUNCTIONS =================

def fetch_tasks():
    try:
        res = supabase.table("scheduler_tasks").select("*").order("task_time").execute()
        return res.data
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return []

def add_task_to_db(name, cat, dt, notes):
    try:
        # Data dictionary with explicit types
        task_data = {
            "name": str(name),
            "category": str(cat),
            "task_time": dt.isoformat(),
            "notes": str(notes) if notes else "",
            "is_archived": False
        }
        supabase.table("scheduler_tasks").insert(task_data).execute()
        return True
    except Exception as e:
        st.error(f"Error saving task: {e}")
        return False

def archive_task_in_db(task_id):
    now_str = datetime.now().strftime("%d-%m %H:%M")
    supabase.table("scheduler_tasks").update({
        "is_archived": True, 
        "archived_on": now_str
    }).eq("id", task_id).execute()

def restore_task_in_db(task_id):
    supabase.table("scheduler_tasks").update({
        "is_archived": False, 
        "archived_on": None
    }).eq("id", task_id).execute()

# ================= APP UI =================

st.title("📱 Smart Scheduler PRO")

# Input Form
with st.expander("➕ Add New Task", expanded=False):
    with st.form("task_form", clear_on_submit=True):
        t_name = st.text_input("Task / Client Name")
        t_cat = st.selectbox("Category", ["Visit", "Pending Order", "Other"])
        col1, col2 = st.columns(2)
        t_date = col1.date_input("Date", datetime.now())
        t_time = col2.time_input("Time", (datetime.now() + timedelta(hours=1)).time())
        t_notes = st.text_area("Notes")
        
        if st.form_submit_button("Save Task"):
            if t_name:
                dt_combined = datetime.combine(t_date, t_time)
                if add_task_to_db(t_name, t_cat, dt_combined, t_notes):
                    st.success("Task Saved Successfully!")
                    st.rerun()
            else:
                st.warning("Pehle Task Name bhariye!")

# Load Data
data = fetch_tasks()
df = pd.DataFrame(data)

if not df.empty:
    # Time formatting
    df['task_time'] = pd.to_datetime(df['task_time'])
    now = datetime.now(df['task_time'].dt.tz)

    tab1, tab2 = st.tabs(["📋 Dashboard", "📦 Archive"])

    with tab1:
        cols = st.columns(3)
        cats = ["Visit", "Pending Order", "Other"]
        
        for i, cat in enumerate(cats):
            with cols[i]:
                st.markdown(f"### {cat}")
                active_tasks = df[(df['category'] == cat) & (df['is_archived'] == False)]
                
                if active_tasks.empty:
                    st.caption("No active tasks.")
                
                for _, row in active_tasks.iterrows():
                    is_overdue = row['task_time'] < now
                    status_class = "overdue" if is_overdue else "upcoming"
                    status_lbl = "⚠️ OVERDUE" if is_overdue else "✅ UPCOMING"
                    
                    st.markdown(f"""
                        <div class="task-card {status_class}">
                            <div style="font-size: 1.1rem;"><strong>{row['name']}</strong></div>
                            <div style="color: #666; font-size: 0.9rem;">⏰ {row['task_time'].strftime('%d %b, %I:%M %p')}</div>
                            <div style="color: {'#dc3545' if is_overdue else '#28a745'}; font-weight: bold; font-size: 0.8rem;">{status_lbl}</div>
                            <div style="margin-top: 5px; font-style: italic; font-size: 0.85rem;">{row['notes'] if row['notes'] else ''}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("Mark Done", key=f"id_{row['id']}"):
                        archive_task_in_db(row['id'])
                        st.rerun()
                    st.write("") # Spacer

    with tab2:
        archived = df[df['is_archived'] == True]
        if not archived.empty:
            for _, row in archived.iterrows():
                with st.container(border=True):
                    col_a, col_b = st.columns([4, 1])
                    col_a.write(f"**{row['name']}** ({row['category']})")
                    col_a.caption(f"Archived on: {row['archived_on']}")
                    if col_b.button("Restore", key=f"res_{row['id']}"):
                        restore_task_in_db(row['id'])
                        st.rerun()
        else:
            st.info("Archive khali hai.")
else:
    st.info("Koi data nahi mila. Naya task add karein!")
