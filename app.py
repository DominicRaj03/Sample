import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Jarvis Executive Suite", layout="wide")

# --- Session State ---
if 'task_completion' not in st.session_state:
    st.session_state.task_completion = {}
if 'defects' not in st.session_state:
    st.session_state.defects = []
if 'manual_overrides' not in st.session_state:
    st.session_state.manual_overrides = {}
if 'resource_away' not in st.session_state:
    st.session_state.resource_away = {}

# --- Balanced Allocation Logic with Availability ---
def run_balanced_allocation(df, dev_names, qa_names):
    task_col = next((c for c in df.columns if "Task" in c), df.columns[1])
    local_df = df.copy()
    dev_tasks = local_df.to_dict('records')
    
    plan = []
    resource_load = {f"Sprint {i}": {name: 0 for name in dev_names + qa_names + ["Designer", "DevOps"]} for i in range(5)}

    def assign_to_least_loaded(sprint, names, task_name, role):
        # 1. Check for Manual Override
        override_key = f"{sprint}_{task_name}"
        if override_key in st.session_state.manual_overrides:
            return {"Sprint": sprint, "Task": task_name, "Owner": st.session_state.manual_overrides[override_key], "Role": role}
        
        # 2. Filter available resources for this sprint
        available = [n for n in names if not st.session_state.resource_away.get(f"{sprint}_{n}", False)]
        
        # Fallback if everyone is away (assign to first person but flag error)
        if not available:
            best_choice = names[0]
        else:
            eligible_load = {name: resource_load[sprint][name] for name in available}
            best_choice = min(eligible_load, key=eligible_load.get)
        
        resource_load[sprint][best_choice] += 1
        return {"Sprint": sprint, "Task": task_name, "Owner": best_choice, "Role": role}

    # Sprint 0: Planning
    plan.append(assign_to_least_loaded("Sprint 0", [dev_names[0]], "SRS Documentation", "Dev"))
    plan.append({"Sprint": "Sprint 0", "Task": "UI/UX Mockups", "Owner": "Designer", "Role": "Design"})

    # Sprint 1 & 2: Development Split
    half = len(dev_tasks) // 2
    for task in dev_tasks[:half]:
        plan.append(assign_to_least_loaded("Sprint 1", dev_names, task[task_col], "Dev"))
    plan.append(assign_to_least_loaded("Sprint 1", qa_names, "QA: Test Mapping", "QA"))

    for task in dev_tasks[half:]:
        plan.append(assign_to_least_loaded("Sprint 2", dev_names, task[task_col], "Dev"))
    plan.append(assign_to_least_loaded("Sprint 2", qa_names, "QA: Execute Sprint 1", "QA"))

    # Sprint 3: Testing & Fixes
    plan.append(assign_to_least_loaded("Sprint 3", qa_names, "QA: Execute Sprint 2", "QA"))
    for bug in st.session_state.defects:
        plan.append(assign_to_least_loaded("Sprint 3", dev_names, f"FIX: {bug['title']}", "Dev"))

    # Sprint 4: Launch
    plan.append({"Sprint": "Sprint 4", "Task": "Final Deployment", "Owner": "DevOps", "Role": "Ops"})
    
    return pd.DataFrame(plan)

# --- Sidebar: Configuration ---
with st.sidebar:
    st.header("👥 Team Setup")
    d_size = st.number_input("Dev Team Size", 1, 10, 2)
    q_size = st.number_input("QA Team Size", 1, 10, 1)
    
    dev_names = [st.text_input(f"Dev {i+1} Name", f"Developer {i+1}", key=f"dn_{i}") for i in range(d_size)]
    qa_names = [st.text_input(f"QA {i+1} Name", f"Tester {i+1}", key=f"qn_{i}") for i in range(q_size)]
    
    st.divider()
    uploaded_file = st.file_uploader("Upload Backlog", type=['xlsx', 'csv'])

# --- Main App ---
if uploaded_file:
    df_raw = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    
    tabs = st.tabs(["📊 Roadmap", "🌴 Attendance", "🔄 Manual Override", "🏁 Tracker"])
    
    with tabs[1]:
        st.header("Resource Availability Matrix")
        st.info("Uncheck if a team member is on leave for a specific sprint.")
        all_members = dev_names + qa_names
        for s in range(5):
            s_name = f"Sprint {s}"
            with st.expander(f"Availability for {s_name}"):
                cols = st.columns(len(all_members))
                for idx, member in enumerate(all_members):
                    is_available = not st.session_state.resource_away.get(f"{s_name}_{member}", False)
                    with cols[idx]:
                        status = st.checkbox(member, value=is_available, key=f"avail_{s_name}_{member}")
                        st.session_state.resource_away[f"{s_name}_{member}"] = not status

    # Run allocation AFTER checking availability
    final_plan = run_balanced_allocation(df_raw, dev_names, qa_names)

    with tabs[0]:
        st.header("Balanced Roadmap")
        load_df = final_plan.groupby(['Sprint', 'Owner']).size().reset_index(name='Tasks')
        st.plotly_chart(px.bar(load_df, x="Sprint", y="Tasks", color="Owner", barmode="group"))
        st.dataframe(final_plan, use_container_width=True)

    with tabs[2]:
        st.header("Resource Swap Tool")
        s_ov = st.selectbox("Sprint:", [f"Sprint {i}" for i in range(5)])
        for _, row in final_plan[final_plan['Sprint'] == s_ov].iterrows():
            col1, col2 = st.columns([2, 1])
            with col1: st.write(f"**{row['Task']}** ({row['Owner']})")
            with col2:
                eligible = dev_names if row['Role'] == "Dev" else qa_names if row['Role'] == "QA" else [row['Owner']]
                new_owner = st.selectbox("Assign to:", eligible, key=f"ov_{s_ov}_{row['Task']}", index=eligible.index(row['Owner']) if row['Owner'] in eligible else 0)
                if new_owner != row['Owner']:
                    st.session_state.manual_overrides[f"{s_ov}_{row['Task']}"] = new_owner
                    st.rerun()

    with tabs[3]:
        s_curr = st.selectbox("Tracker Sprint:", [f"Sprint {i}" for i in range(5)])
        for _, row in final_plan[final_plan['Sprint'] == s_curr].iterrows():
            t_key = f"{s_curr}_{row['Task']}"
            st.session_state.task_completion[t_key] = st.checkbox(f"[{row['Owner']}] {row['Task']}", value=st.session_state.task_completion.get(t_key, False))

else:
    st.info("Jarvis: Awaiting data to initialize the Availability Control Suite.")
