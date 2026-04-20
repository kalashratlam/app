import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd
import pytz

# IST Timezone setup
IST = pytz.timezone('Asia/Kolkata')

# ================= DATABASE CONNECTIVITY =================
SUPABASE_URL = "https://knjfotknwxlrjscuyoir.supabase.co"
SUPABASE_KEY = "sb_publishable_wwT5nUUkokrcwVod12R6TQ_fy57CDZA"

@st.cache_resource
def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

# ================= UI & CSS =================
st.set_page_config(page_title="Smart Scheduler PRO", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f0f2f5; }
    .table-header { padding: 10px; color: white; font-weight: bold; text-align: center; border-radius: 5px 5px 0 0; }
    [data-testid="column"] { min-width: 320px !important; }
    .task-card { background-color: white; padding: 12px; border-bottom: 1px solid #eee; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .status-upcoming { color: #28a745; font-weight: bold; font-size: 0.8rem; }
    .status-overdue { color: #dc3545; font-weight: bold; font-size: 0.8rem; }
    .stButton>button { border-radius: 4px; height: 30px; font-size: 0.8rem; margin-top: 5px; width: 100%; }
    .archive-item { background-color: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 8px; }
    </style>
    """, unsafe_allow_html=True)

if 'editing_task' not in st.session_state:
    st.session_state.editing_task = None

# ================= FUNCTIONS =================
def fetch_tasks():
    try:
        res = supabase.table("scheduler_tasks").select("*").order("task_time").execute()
        raw_data = res.data
        
        # Manual Time Conversion (Error Proof)
        for item in raw_data:
            try:
                # String ko datetime mein badalna aur IST ensure karna
                dt_str = item['task_time'].replace('Z', '+00:00')
                dt_obj = datetime.fromisoformat(dt_str)
                if dt_obj.tzinfo is None:
                    dt_obj = pytz.utc.localize(dt_obj)
                item['task_time_dt'] = dt_obj.astimezone(IST)
            except:
                item['task_time_dt'] = datetime.now(IST) # Fallback
        return raw_data
    except: return []

def save_task(name, cat, dt, notes, task_id=None):
    if dt.tzinfo is None:
        dt = IST.localize(dt)
    data = {"name": str(name), "category": str(cat), "task_time": dt.isoformat(), "notes": str(notes), "is_archived": False}
    if task_id: supabase.table("scheduler_tasks").update(data).eq("id", task_id).execute()
    else: supabase.table("scheduler_tasks").insert(data).execute()

# ================= APP UI =================
st.title("📊 Smart Scheduler PRO")
now_ist = datetime.now(IST)

# --- Top Input Form ---
is_edit = st.session_state.editing_task is not None
with st.container():
    with st.expander("➕ " + ("Edit Task" if is_edit else "Add New Entry"), expanded=is_edit):
        with st.form("input_form", clear_on_submit=not is_edit):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
            d = st.session_state.editing_task if is_edit else {}
            
            t_name = col1.text_input("Name", value=d.get('name', ""))
            t_cat = col2.selectbox("Category", ["Visit", "Pending Order", "Other"], 
                                   index=["Visit", "Pending Order", "Other"].index(d.get('category', 'Visit')))
            
            if is_edit:
                dt_obj = d['task_time_dt']
                d_val, t_val = dt_obj.date(), dt_obj.time()
            else:
                d_val, t_val = now_ist.date(), (now_ist + timedelta(hours=1)).time()
                
            t_date = col3.date_input("Date", d_val)
            t_time = col3.time_input("Time", t_val)
            t_notes = col4.text_input("Notes", value=d.get('notes', ""))
            
            if st.form_submit_button("Save Changes" if is_edit else "Add Task"):
                dt_c = IST.localize(datetime.combine(t_date, t_time))
                save_task(t_name, t_cat, dt_c, t_notes, d.get('id'))
                st.session_state.editing_task = None
                st.rerun()
        if is_edit:
            if st.button("Cancel Edit"):
                st.session_state.editing_task = None
                st.rerun()

# --- Dashboard ---
data = fetch_tasks()

if data:
    dashboard_cols = st.columns(3)
    cats = [("Visit", "#28a745"), ("Pending Order", "#dc3545"), ("Other", "#007bff")]

    for i, (cat_name, cat_color) in enumerate(cats):
        with dashboard_cols[i]:
            st.markdown(f'<div class="table-header" style="background-color:{cat_color}">{cat_name}</div>', unsafe_allow_html=True)
            
            # Filter active tasks for this category
            active = [t for t in data if t['category'] == cat_name and not t['is_archived']]
            
            for row in active:
                overdue = row['task_time_dt'] < now_ist
                st_text = "OVERDUE" if overdue else "UPCOMING"
                st_class = "status-overdue" if overdue else "status-upcoming"
                
                st.markdown(f"""
                <div class="task-card">
                    <div style="display:flex; justify-content:space-between;"><b>{row['name']}</b><span class="{st_class}">{st_text}</span></div>
                    <div style="font-size:0.8rem; color:#666;">📅 {row['task_time_dt'].strftime('%d-%m-%y')} | ⏰ {row['task_time_dt'].strftime('%H:%M')}</div>
                    <div style="font-size:0.75rem; color:#888;">{row['notes']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                if c1.button("Edit", key=f"e_{row['id']}"):
                    st.session_state.editing_task = row
                    st.rerun()
                if c2.button("Archive", key=f"a_{row['id']}"):
                    supabase.table("scheduler_tasks").update({"is_archived": True, "archived_on": now_ist.strftime("%d-%m %H:%M")}).eq("id", row['id']).execute()
                    st.rerun()

    # --- Archive Section ---
    st.markdown("---")
    st.subheader("📦 Archive Records")
    archived = [t for t in data if t['is_archived']]
    
    if archived:
        for row in archived:
            with st.container():
                ca1, ca2 = st.columns([5, 1])
                ca1.markdown(f"""
                <div class="archive-item">
                    <strong>{row['name']}</strong> | {row['category']}<br>
                    <small>Set for: {row['task_time_dt'].strftime('%d-%m %H:%M')} | Archived: {row['archived_on']}</small>
                </div>
                """, unsafe_allow_html=True)
                if ca2.button("Restore", key=f"res_{row['id']}"):
                    supabase.table("scheduler_tasks").update({"is_archived": False, "archived_on": None}).eq("id", row['id']).execute()
                    st.rerun()
    else:
        st.write("Archive khali hai.")
else:
    st.info("Abhi koi task nahi hai.")
