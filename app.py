import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd
import pytz

# IST Timezone
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
    [data-testid="column"] { min-width: 300px !important; }
    .task-card { background-color: white; padding: 12px; border-bottom: 1px solid #eee; }
    .status-upcoming { color: #28a745; font-weight: bold; font-size: 0.8rem; }
    .status-overdue { color: #dc3545; font-weight: bold; font-size: 0.8rem; }
    .stButton>button { border-radius: 4px; height: 28px; line-height: 10px; font-size: 0.8rem; margin-top: 5px; }
    .archive-card { background-color: #e9ecef; padding: 10px; border-radius: 5px; margin-bottom: 5px; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

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
now_ist = datetime.now(IST)

# --- Top Input Form ---
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
                dt_obj = pd.to_datetime(d['task_time']).astimezone(IST)
                d_val, t_val = dt_obj.date(), dt_obj.time()
            else:
                d_val, t_val = now_ist.date(), (now_ist + timedelta(hours=1)).time()
            t_date = col3.date_input("Date", d_val)
            t_time = col3.time_input("Time", t_val)
            t_notes = col4.text_input("Notes", value=d.get('notes', ""))
            if st.form_submit_button("Save"):
                dt_c = IST.localize(datetime.combine(t_date, t_time))
                save_task(t_name, t_cat, dt_c, t_notes, d.get('id'))
                st.session_state.editing_task = None
                st.rerun()

# --- Dashboard ---
data = fetch_tasks()
df = pd.DataFrame(data)

if not df.empty:
    # Convert all times to IST for display
    df['task_time'] = pd.to_datetime(df['task_time']).dt.tz_convert('Asia/Kolkata')
    
    dashboard_cols = st.columns(3)
    cats = [("Visit", "#28a745"), ("Pending Order", "#dc3545"), ("Other", "#007bff")]

    for i, (cat_name, cat_color) in enumerate(cats):
        with dashboard_cols[i]:
            st.markdown(f'<div class="table-header" style="background-color:{cat_color}">{cat_name}</div>', unsafe_allow_html=True)
            active = df[(df['category'] == cat_name) & (df['is_archived'] == False)]
            for _, row in active.iterrows():
                overdue = row['task_time'] < now_ist
                st_text = "OVERDUE" if overdue else "UPCOMING"
                st_class = "status-overdue" if overdue else "status-upcoming"
                st.markdown(f"""
                <div class="task-card">
                    <div style="display:flex; justify-content:space-between;"><b>{row['name']}</b><span class="{st_class}">{st_text}</span></div>
                    <div style="font-size:0.8rem; color:#666;">📅 {row['task_time'].strftime('%d-%m-%y')} | ⏰ {row['task_time'].strftime('%H:%M')}</div>
                    <div style="font-size:0.75rem; color:#888;">{row['notes']}</div>
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("Edit", key=f"e_{row['id']}"):
                    st.session_state.editing_task = row.to_dict()
                    st.rerun()
                if c2.button("Done", key=f"a_{row['id']}"):
                    supabase.table("scheduler_tasks").update({"is_archived": True, "archived_on": now_ist.strftime("%d-%m %H:%M")}).eq("id", row['id']).execute()
                    st.rerun()

    # --- Archive Section (Fixed) ---
    st.markdown("---")
    st.subheader("📦 Archived Tasks")
    archived = df[df['is_archived'] == True]
    
    if not archived.empty:
        # Displaying archived tasks in a cleaner list
        for _, row in archived.iterrows():
            with st.container():
                col_arch1, col_arch2 = st.columns([5, 1])
                with col_arch1:
                    st.markdown(f"""
                    <div class="archive-card">
                        <strong>{row['name']}</strong> ({row['category']})<br>
                        <small>Was set for: {row['task_time'].strftime('%d-%m %H:%M')} | Archived on: {row['archived_on']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                with col_arch2:
                    if st.button("Restore", key=f"res_{row['id']}"):
                        supabase.table("scheduler_tasks").update({"is_archived": False, "archived_on": None}).eq("id", row['id']).execute()
                        st.rerun()
    else:
        st.info("Archive mein koi data nahi hai.")
else:
    st.info("Koi tasks nahi hain. Upar '+' se add karein.")
