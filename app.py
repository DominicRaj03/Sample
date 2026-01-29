import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Jarvis Executive Suite", layout="wide")

# --- Session State Initialization ---
if 'task_completion' not in st.session_state:
    st.session_state.task_completion = {}
if 'defects' not in st.session_state:
    st.session_state.defects = []
if 'manual_overrides' not in st.session_state:
    st.session_state.manual_overrides = {}
if 'resource_away' not in st.session_state:
    st.session_state.resource_away = {}

# --- Logic Core ---
def run_balanced_allocation(df, dev_names, qa_names):
    task_col = next((c for c in df.columns if "Task" in c), df.columns[1])
    local_df = df.copy()
    dev_tasks = local_df.to_dict('records')
    
    plan = []
    # Initialize load trackers
    resource_load = {f"Sprint {i}": {name: 0 for name in dev_names + qa_names + ["Designer", "DevOps"]} for i in range(5)}

    def assign_to_least_loaded(sprint, names, task_name, role):
        override_key = f"{sprint}_{task_name}"
        
        # 1. Manual Override check
        if override_key in st.session_state.manual_overrides:
            assigned_owner = st.session_state.manual_overrides[override_key]
        else:
            # 2. Availability Check
            available = [n for n in names if not st.session_state.resource_away.get(f"{sprint}_{n}", False)]
            if not available:
                assigned_owner = names[0] # Fallback
            else:
                # 3. Load Balancing
                eligible_load = {name: resource_load[sprint][name] for name in available}
                assigned_owner = min(eligible_load, key=eligible_load.get)
        
        resource_load[sprint][assigned_owner] += 1
        return {"Sprint": sprint, "Task": task_name, "Owner": assigned_owner, "Role": role}

    # Allocation Sequence
    plan.append(assign_to_least_loaded("Sprint 0", [dev_names[0]], "SRS Documentation", "Dev"))
    plan.append({"Sprint": "Sprint 0", "Task": "UI/UX Mockups", "Owner": "Designer", "Role": "Design"})

    half = len(dev_tasks) // 2
    for task in dev_tasks[:half]:
        plan.append(assign_to_least_loaded("Sprint 1", dev_names, task[task_col], "Dev"))
    plan.append(assign_to_least_loaded("Sprint 1", qa_names, "QA: Test Mapping", "QA"))

    for task in dev_tasks[half:]:
        plan.append(assign_to_least_loaded("Sprint 2", dev_names, task[task_col], "Dev"))
    plan.append(assign_to_least_loaded("Sprint 2", qa_names, "QA: Execute Sprint 1", "QA"))

    plan.append(assign_to_least_loaded("Sprint 3", qa_names, "QA: Execute Sprint 2", "QA"))
    for bug in st.session_state.defects:
        plan.append(assign_to_least_loaded("Sprint 3", dev_names, f"FIX: {bug['title']}", "Dev"))

    plan.append({"Sprint": "Sprint 4", "Task": "Final Deployment", "Owner": "DevOps", "Role": "Ops"})
    
    return pd.DataFrame(plan)

# --- Sidebar ---
with st.sidebar:
    st.header("👥 Team Setup")
    d_size = st.number_input("Dev Team Size", 1, 10, 2)
    q_size = st.number_input("QA Team Size", 1, 10, 1)
    
    dev_names = [st.text_input(f"Dev {i+1}", f"Developer {i+1}", key=f"dn_{i}") for i in range(d_size)]
    qa_names = [st.text_input(f"QA {i+1}", f"Tester {i+1}", key=f"qn_{i}") for i in range(q_size)]
    
    uploaded_file = st.file_uploader("Upload Backlog", type=['xlsx', 'csv'])

# --- App Execution ---
if uploaded_file:
    df_raw = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    
    # Calculate Plan
    final_plan = run_balanced_allocation(df_raw, dev_names, qa_names)
    
    tabs = st.tabs(["📊 Roadmap", "🌴 Availability", "🔄 Resource Swap", "🏁 Tracker"])
    
    with tabs[1]:
        st.header("Attendance Matrix")
        all_members = dev_names + qa_names
        for s in range(5):
            s_name = f"Sprint {s}"
            cols = st.columns(len(all_members))
            for idx, member in enumerate(all_members):
                key = f"{s_name}_{member}"
                is_avail = not st.session_state.resource_away.get(key, False)
                with cols[idx]:
                    if not st.checkbox(f"{member} (S{s})", value=is_avail, key=f"cb_{key}"):
                        st.session_state.resource_away[key] = True
                    else:
                        st.session_state.resource_away[key] = False

    with tabs[0]:
        st.header("Balanced Roadmap")
        load_df = final_plan.groupby(['Sprint', 'Owner']).size().reset_index(name='Tasks')
        # Fix: Using Plotly safely
        fig = px.bar(load_df, x="Sprint", y="Tasks", color="Owner", barmode="group", title="Task Distribution")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(final_plan, use_container_width=True)

    with tabs[2]:
        st.header("Manual Override")
        s_sel = st.selectbox("Sprint:", [f"Sprint {i}" for i in range(5)])
        s_tasks = final_plan[final_plan['Sprint'] == s_sel]
        for _, row in s_tasks.iterrows():
            c1, c2 = st.columns([2, 1])
            with c1: st.write(f"**{row['Task']}**")
            with c2:
                eligible = dev_names if row['Role'] == "Dev" else qa_names if row['Role'] == "QA" else [row['Owner']]
                choice = st.selectbox("Assign to:", eligible, key=f"sw_{s_sel}_{row['Task']}", index=eligible.index(row['Owner']) if row['Owner'] in eligible else 0)
                if choice != row['Owner']:
                    st.session_state.manual_overrides[f"{s_sel}_{row['Task']}"] = choice
                    st.rerun()

    with tabs[3]:
        s_curr = st.selectbox("Status Update:", [f"Sprint {i}" for i in range(5)])
        for _, row in final_plan[final_plan['Sprint'] == s_curr].iterrows():
            t_key = f"{s_curr}_{row['Task']}"
            st.session_state.task_completion[t_key] = st.checkbox(f"[{row['Owner']}] {row['Task']}", value=st.session_state.task_completion.get(t_key, False))
else:
    st.info("Jarvis: Please upload the backlog to activate the Resource Engine.")
