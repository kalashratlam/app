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

# ================= LOGIN SYSTEM =================
def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user = ""

    if st.session_state.authenticated:
        return True

    # Login UI Styling
    st.markdown("""
        <style>
        .login-box {
            background-color: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        </style>
        """, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align: center; color: #007bff;'>💼 Smart Scheduler PRO</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container():
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            u_input = st.text_input("Username")
            p_input = st.text_input("Password", type="password")
            
            if st.button("Login", use_container_width=True):
                # Supabase se user check karna
                res = supabase.table("app_users").select("*").eq("username", u_input).eq("password", p_input).execute()
                
                if res.data:
                    st.session_state.authenticated = True
                    st.session_state.user = u_input
                    st.rerun()
                else:
                    st.error("❌ Username ya Password galat hai!")
            st.markdown('</div>', unsafe_allow_html=True)
    return False

# ================= MAIN APP =================
if check_auth():
    # Page Setup
    st.set_page_config(page_title="Dashboard | Smart Scheduler", layout="wide")
    
    # Sidebar Info
    st.sidebar.title(f"👤 Welcome, {st.session_state.user}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

    # Dashboard CSS
    st.markdown("""
        <style>
        .stApp { background-color: #f0f2f5; }
        .table-header { padding: 10px; color: white; font-weight: bold; text-align: center; border-radius: 8px 8px 0 0; margin-top: 10px; }
        [data-testid="column"] { min-width: 320px !important; }
        .task-card { background-color: white; padding: 15px; border-bottom: 1px solid #eee; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .status-upcoming { color: #28a745; font-weight: bold; }
        .status-overdue { color: #dc3545; font-weight: bold; }
        .stButton>button { border-radius: 5px; height: 30px; font-size: 0.8rem; margin-top: 2px; }
        </style>
        """, unsafe_allow_html=True)

    if 'editing_task' not in st.session_state:
        st.session_state.editing_task = None

    # --- Database Functions ---
    def fetch_tasks():
        try:
            res = supabase.table("scheduler_tasks").select("*").order("task_time").execute()
            raw_data = res.data
            for item in raw_data:
                try:
                    dt_str = item['task_time'].replace('Z', '+00:00')
                    dt_obj = datetime.fromisoformat(dt_str)
                    if dt_obj.tzinfo is None: dt_obj = pytz.utc.localize(dt_obj)
                    item['task_time_dt'] = dt_obj.astimezone(IST)
                except: item['task_time_dt'] = datetime.now(IST)
            return raw_data
        except: return []

    def save_task(name, cat, dt, notes, task_id=None):
        if dt.tzinfo is None: dt = IST.localize(dt)
        data = {"name": str(name), "category": str(cat), "task_time": dt.isoformat(), "notes": str(notes), "is_archived": False}
        if task_id: supabase.table("scheduler_tasks").update(data).eq("id", task_id).execute()
        else: supabase.table("scheduler_tasks").insert(data).execute()

    def snooze_task(task_id, current_time, hours=0, days=0):
        new_time = current_time + timedelta(hours=hours, days=days)
        supabase.table("scheduler_tasks").update({"task_time": new_time.isoformat()}).eq("id", task_id).execute()

    # --- Dashboard UI ---
    st.title("📊 Task Management Dashboard")
    now_ist = datetime.now(IST)

    # Entry/Edit Form
    is_edit = st.session_state.editing_task is not None
    with st.expander("➕ " + ("Edit Current Task" if is_edit else "Add New Entry"), expanded=is_edit):
        with st.form("input_form", clear_on_submit=not is_edit):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
            d = st.session_state.editing_task if is_edit else {}
            
            t_name = c1.text_input("Client / Task Name", value=d.get('name', ""))
            t_cat = c2.selectbox("Category", ["Visit", "Pending Order", "Other"], 
                                 index=["Visit", "Pending Order", "Other"].index(d.get('category', 'Visit')))
            
            if is_edit:
                dt_obj = d['task_time_dt']
                d_val, t_val = dt_obj.date(), dt_obj.time()
            else:
                d_val, t_val = now_ist.date(), (now_ist + timedelta(hours=1)).time()
                
            t_date = c3.date_input("Date", d_val)
            t_time = c3.time_input("Time", t_val)
            t_notes = c4.text_input("Notes", value=d.get('notes', ""))
            
            if st.form_submit_button("Save Changes" if is_edit else "Add Task"):
                dt_c = IST.localize(datetime.combine(t_date, t_time))
                save_task(t_name, t_cat, dt_c, t_notes, d.get('id'))
                st.session_state.editing_task = None
                st.rerun()

    # Display Columns
    data = fetch_tasks()
    if data:
        dashboard_cols = st.columns(3)
        cats = [("Visit", "#28a745"), ("Pending Order", "#dc3545"), ("Other", "#007bff")]
        for i, (cat_name, cat_color) in enumerate(cats):
            with dashboard_cols[i]:
                st.markdown(f'<div class="table-header" style="background-color:{cat_color}">{cat_name}</div>', unsafe_allow_html=True)
                active_list = [t for t in data if t['category'] == cat_name and not t['is_archived']]
                for row in active_list:
                    overdue = row['task_time_dt'] < now_ist
                    st_text, st_class = ("OVERDUE", "status-overdue") if overdue else ("UPCOMING", "status-upcoming")
                    
                    st.markdown(f"""
                    <div class="task-card">
                        <div style="display:flex; justify-content:space-between;">
                            <b>{row['name']}</b>
                            <span class="{st_class}">{st_text}</span>
                        </div>
                        <div style="font-size:0.8rem; color:#666;">⏰ {row['task_time_dt'].strftime('%d-%m %H:%M')}</div>
                        <div style="font-size:0.75rem; color:#888; margin-top:4px;"><i>{row['notes']}</i></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Actions
                    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1.5])
                    if btn_col1.button("Edit", key=f"e_{row['id']}"):
                        st.session_state.editing_task = row
                        st.rerun()
                    if btn_col2.button("Done", key=f"a_{row['id']}"):
                        supabase.table("scheduler_tasks").update({"is_archived": True, "archived_on": now_ist.strftime("%d-%m %H:%M")}).eq("id", row['id']).execute()
                        st.rerun()
                    with btn_col3:
                        snooze_opt = st.selectbox("Snooze", ["-", "1 Hr", "1 Day"], key=f"sz_{row['id']}", label_visibility="collapsed")
                        if snooze_opt == "1 Hr":
                            snooze_task(row['id'], row['task_time_dt'], hours=1)
                            st.rerun()
                        elif snooze_opt == "1 Day":
                            snooze_task(row['id'], row['task_time_dt'], days=1)
                            st.rerun()
