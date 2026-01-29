import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Executive Suite", layout="wide")

# --- Session State ---
if 'task_completion' not in st.session_state:
    st.session_state.task_completion = {}
if 'defects' not in st.session_state:
    st.session_state.defects = []

# --- Core Phase Logic ---
def run_phase_gate_allocation(df):
    task_col = next((c for c in df.columns if "Task" in c), df.columns[1])
    hour_col = next((c for c in df.columns if "Hours" in c or "Effort" in c), df.columns[-1])
    
    local_df = df.copy()
    local_df[hour_col] = pd.to_numeric(local_df[hour_col], errors='coerce').fillna(0)
    dev_tasks = local_df.to_dict('records')
    half = len(dev_tasks) // 2
    
    plan = []
    # Sprint 0: Planning
    plan.append({"Sprint": "Sprint 0", "Task": "SRS Documentation", "Role": "Lead", "Phase": "Planning"})
    plan.append({"Sprint": "Sprint 0", "Task": "UI/UX Mockups", "Role": "Design", "Phase": "Planning"})
    # Sprint 1: Dev Alpha
    for task in dev_tasks[:half]:
        plan.append({"Sprint": "Sprint 1", "Task": task[task_col], "Role": "Dev", "Phase": "Execution"})
    # Sprint 2: Dev Beta & QA 1
    for task in dev_tasks[half:]:
        plan.append({"Sprint": "Sprint 2", "Task": task[task_col], "Role": "Dev", "Phase": "Execution"})
    plan.append({"Sprint": "Sprint 2", "Task": "QA: Execution Sprint 1", "Role": "QA", "Phase": "Testing"})
    # Sprint 3: QA 2 & Bug Fix
    plan.append({"Sprint": "Sprint 3", "Task": "QA: Execution Sprint 2", "Role": "QA", "Phase": "Testing"})
    for bug in st.session_state.defects:
        plan.append({"Sprint": "Sprint 3", "Task": f"FIX: {bug['title']}", "Role": "Dev", "Phase": "Stabilization"})
    # Sprint 4: Launch
    plan.append({"Sprint": "Sprint 4", "Task": "Deployment & Go-Live", "Role": "DevOps", "Phase": "Launch"})
    
    return pd.DataFrame(plan)

# --- UI Setup ---
with st.sidebar:
    st.header("⚙️ Project Setup")
    uploaded_file = st.file_uploader("Upload Work Items", type=['xlsx', 'csv'])
    p_name = st.text_input("Project Name", "Project Jarvis-Alpha")
    p_lead = st.text_input("Project Lead", "Executive User")
    start_date = st.date_input("Start Date", datetime(2026, 1, 27))

if uploaded_file:
    df_raw = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    final_plan = run_phase_gate_allocation(df_raw)
    
    tabs = st.tabs(["🚀 Roadmap", "🏁 Status", "📜 Project Charter"])
    
    with tabs[2]:
        st.header("Project Charter")
        
        # Charter Content Construction
        charter_html = f"""
        # PROJECT CHARTER: {p_name}
        
        **Date:** {datetime.now().strftime('%Y-%m-%d')}  
        **Project Lead:** {p_lead}  
        **Start Date:** {start_date}
        
        ## 1. Objectives
        * Deliver full functional requirements based on provided backlog.
        * Maintain zero high-severity defects at time of launch.
        * Complete sequential 5-sprint delivery cycle.
        
        ## 2. Project Scope & Phases
        * **Sprint 0:** SRS & Design Foundations.
        * **Sprint 1 & 2:** Core Development & Staggered QA.
        * **Sprint 3:** Stabilization & Bug Remediation.
        * **Sprint 4:** Final Deployment.
        
        ## 3. Current Quality Status
        * Total Defects Logged: {len(st.session_state.defects)}
        * Open Blocker Issues: {len([b for b in st.session_state.defects if b['severity'] == "High"])}
        
        ## 4. Sign-off Authorization
        __________________________  
        Executive Sponsor
        """
        
        st.markdown(charter_html)
        
        # Download Logic (Markdown/Text format for immediate portability)
        st.download_button(
            label="📥 Download Project Charter",
            data=charter_html,
            file_name=f"{p_name.replace(' ', '_')}_Charter.md",
            mime="text/markdown"
        )
        st.info("Jarvis: You can save this Markdown file as a PDF using any standard editor (Word, VS Code, or Browser).")

    with tabs[0]:
        st.header("Phase-Gate Roadmap")
        st.dataframe(final_plan, use_container_width=True)

    with tabs[1]:
        s_select = st.selectbox("Update Sprint:", [f"Sprint {i}" for i in range(5)])
        curr_tasks = final_plan[final_plan['Sprint'] == s_select]
        for _, row in curr_tasks.iterrows():
            t_key = f"{s_select}_{row['Task']}"
            st.session_state.task_completion[t_key] = st.checkbox(f"{row['Task']} ({row['Role']})", value=st.session_state.task_completion.get(t_key, False))
else:
    st.info("Jarvis: Upload backlog to generate the Charter and Roadmap.")
