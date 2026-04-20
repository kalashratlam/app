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

# ================= UI & CSS (FOR SCREENSHOT LOOK) =================
st.set_page_config(page_title="Smart Scheduler PRO", layout="wide")

st.markdown("""
    <style>
    /* Main Background */
    .stApp { background-color: #f0f2f5; }
    
    /* Header Styles */
    .table-header {
        padding: 10px;
        color: white;
        font-weight: bold;
        text-align: center;
        border-radius: 5px 5px 0 0;
        margin-bottom: 0px;
    }
    
    /* Force Horizontal Columns even on Mobile */
    [data-testid="column"] {
        min-width: 300px !important;
    }
    
    /* Task Card Look */
    .task-card {
        background-color: white;
        padding: 12px;
        border-bottom: 1px solid #eee;
        font-family: 'Segoe UI', sans-serif;
    }
    
    .status-upcoming { color: #28a745; font-weight: bold; font-size: 0.8rem; }
    .status-overdue { color: #dc3545; font-weight: bold; font-size: 0.8rem; }
    
    /* Button Styling */
    .stButton>button {
        border-radius: 4px;
        height: 25px;
        line-height: 10px;
        font-size: 0.7rem;
        margin-top: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# ================= SESSION STATE =================
if 'editing_task' not in st.session_state:
    st.session_state.editing_task = None

# ================= FUNCTIONS =================
def fetch_tasks():
    try:
        res = supabase.table("scheduler_tasks").select("*").order("task_time").execute()
        return res.data
    except: return []

def save_task(name, cat, dt, notes, task_id=None):
    data = {"name": str(name), "category": str(cat), "task_time": dt.isoformat(), "notes": str(notes), "is_archived": False}
    if task_id: supabase.table("scheduler_tasks").update(data).eq("id", task_id).execute()
    else: supabase.table("scheduler_tasks").insert(data).execute()

# ================= APP UI =================
st.title("📊 Smart Scheduler PRO")

# --- Top Input Form (Screenshot jaisa compact) ---
is_edit = st.session_state.editing_task is not None
with st.container():
    with st.expander("➕ " + ("Edit Task" if is_edit else "Add New Entry"), expanded=is_edit):
        with st.form("input_form"):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
            
            d = st.session_state.editing_task if is_edit else {}
            
            t_name = col1.text_input("Name", value=d.get('name', ""))
            t_cat = col2.selectbox("Category", ["Visit", "Pending Order", "Other"], 
                                   index=["Visit", "Pending Order", "Other"].index(d.get('category', 'Visit')))
            
            if is_edit:
                dt_obj = pd.to_datetime(d['task_time'])
                d_val, t_val = dt_obj.date(), dt_obj.time()
            else:
                d_val, t_val = datetime.now().date(), (datetime.now() + timedelta(hours=1)).time()
                
            t_date = col3.date_input("Date", d_val)
            t_time = col3.time_input("Time", t_val)
            t_notes = col4.text_input("Notes / Remarks", value=d.get('notes', ""))
            
            sub_col1, sub_col2 = st.columns([1, 5])
            if sub_col1.form_submit_button("Save"):
                dt_c = datetime.combine(t_date, t_time)
                save_task(t_name, t_cat, dt_c, t_notes, d.get('id'))
                st.session_state.editing_task = None
                st.rerun()
            if is_edit:
                if sub_col2.form_submit_button("Cancel"):
                    st.session_state.editing_task = None
                    st.rerun()

# --- Main Dashboard (3 Columns like Screenshot) ---
data = fetch_tasks()
df = pd.DataFrame(data)

if not df.empty:
    df['task_time'] = pd.to_datetime(df['task_time'])
    now = datetime.now(df['task_time'].dt.tz)
    
    # 3 main columns set karna
    dashboard_cols = st.columns(3)
    cats = [("Visit", "#28a745"), ("Pending Order", "#dc3545"), ("Other", "#007bff")]

    for i, (cat_name, cat_color) in enumerate(cats):
        with dashboard_cols[i]:
            # Table Header
            st.markdown(f'<div class="table-header" style="background-color:{cat_color}">{cat_name}</div>', unsafe_allow_html=True)
            
            active = df[(df['category'] == cat_name) & (df['is_archived'] == False)]
            
            if active.empty:
                st.markdown('<div class="task-card" style="text-align:center; color:#999;">No tasks</div>', unsafe_allow_html=True)
            
            for _, row in active.iterrows():
                overdue = row['task_time'] < now
                st_text = "OVERDUE" if overdue else "UPCOMING"
                st_class = "status-overdue" if overdue else "status-upcoming"
                
                # Task Card Body
                st.markdown(f"""
                <div class="task-card">
                    <div style="display:flex; justify-content:space-between;">
                        <b>{row['name']}</b>
                        <span class="{st_class}">{st_text}</span>
                    </div>
                    <div style="font-size:0.8rem; color:#666;">
                        📅 {row['task_time'].strftime('%d-%m-%y')} | ⏰ {row['task_time'].strftime('%H:%M')}
                    </div>
                    <div style="font-size:0.75rem; color:#888; margin-top:3px;"><i>{row['notes']}</i></div>
                </div>
                """, unsafe_allow_html=True)
                
                # Buttons niche
                btn_c1, btn_c2 = st.columns(2)
                if btn_c1.button("Edit", key=f"e_{row['id']}"):
                    st.session_state.editing_task = row.to_dict()
                    st.rerun()
                if btn_c2.button("Archive", key=f"a_{row['id']}"):
                    supabase.table("scheduler_tasks").update({"is_archived": True, "archived_on": datetime.now().strftime("%d-%m %H:%M")}).eq("id", row['id']).execute()
                    st.rerun()

    # --- Archive Section at Bottom ---
    st.markdown("---")
    with st.expander("📦 Archived Tasks Records"):
        archived = df[df['is_archived'] == True]
        if not archived.empty:
            st.table(archived[['name', 'category', 'task_time', 'notes', 'archived_on']])
            if st.button("Restore Selected (Click row ID)"):
                st.info("Feature: Use Database to restore directly")
        else:
            st.write("Archive khali hai.")
else:
    st.info("No data available.")
