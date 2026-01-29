import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Scope Negotiator", layout="wide")

# --- Session State ---
if 'manual_overrides' not in st.session_state:
    st.session_state.manual_overrides = {}
if 'resource_away' not in st.session_state:
    st.session_state.resource_away = {}
if 'future_release' not in st.session_state:
    st.session_state.future_release = []

# --- Logic Core ---
def run_architect_allocation(df, dev_names, qa_names, splits):
    task_col = next((c for c in df.columns if "Task" in c), df.columns[1])
    hour_col = next((c for c in df.columns if "Hours" in c or "Effort" in c), df.columns[-1])
    
    local_df = df.copy()
    # Filter out tasks moved to future release
    local_df = local_df[~local_df[task_col].isin(st.session_state.future_release)]
    local_df[hour_col] = pd.to_numeric(local_df[hour_col], errors='coerce').fillna(0)
    
    plan = []
    resource_load = {f"Sprint {i}": {name: 0 for name in dev_names + qa_names + ["Designer", "Lead", "DevOps"]} for i in range(5)}

    def assign_work(sprint, names, task_name, role, hours):
        ov_key = f"{sprint}_{task_name}"
        if ov_key in st.session_state.manual_overrides:
            owner = st.session_state.manual_overrides[ov_key]
        else:
            avail = [n for n in names if not st.session_state.resource_away.get(f"{sprint}_{n}", False)]
            owner = min(avail, key=lambda x: resource_load[sprint][x]) if avail else names[0]
        
        resource_load[sprint][owner] += hours
        return {"Sprint": sprint, "Task": task_name, "Owner": owner, "Role": role, "Hours": hours}

    # Fixed Phase Logic
    plan.append(assign_work("Sprint 0", ["Lead"], "Requirements Analysis", "Lead", splits['Analysis']))
    plan.append(assign_work("Sprint 0", ["Designer"], "UI/UX & Documentation", "Design", splits['Doc']))

    # Dev Tasks Split
    dev_tasks = local_df.to_dict('records')
    half = len(dev_tasks) // 2
    for i, task in enumerate(dev_tasks):
        sprint = "Sprint 1" if i < half else "Sprint 2"
        plan.append(assign_work(sprint, dev_names, task[task_col], "Dev", task[hour_col]))
        plan.append(assign_work(sprint, dev_names, f"Review: {task[task_col]}", "Dev", splits['Review']))

    plan.append(assign_work("Sprint 3", qa_names, "QA Execution", "QA", splits['QA']))
    plan.append(assign_work("Sprint 3", dev_names, "Bug Fixes", "Dev", splits['Fixes']))
    plan.append(assign_work("Sprint 3", qa_names, "Retest", "QA", splits['Retest']))
    plan.append(assign_work("Sprint 4", ["DevOps"], "Deployment", "Ops", splits['Deploy']))
    
    return pd.DataFrame(plan)

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Capacity & Splits")
    sprint_days = st.number_input("Sprint Days", 1, 30, 12)
    daily_hrs = st.slider("Daily Work Hours", 4, 12, 8)
    max_cap = sprint_days * daily_hrs
    
    st.divider()
    splits = {
        'Analysis': st.number_input("Analysis Phase", 0, 500, 40),
        'Review': st.number_input("Review (per task)", 0, 20, 2),
        'QA': st.number_input("QA Phase", 0, 500, 80),
        'Fixes': st.number_input("Bug Fixes", 0, 500, 40),
        'Retest': st.number_input("Bug Retest", 0, 500, 20),
        'Doc': st.number_input("Documentation", 0, 500, 30),
        'Deploy': st.number_input("Deployment", 0, 500, 16)
    }

    st.header("👥 Team")
    d_size = st.number_input("Dev Size", 1, 10, 2)
    q_size = st.number_input("QA Size", 1, 10, 1)
    dev_names = [st.text_input(f"Dev {i+1}", f"Dev {i+1}", key=f"dn_{i}") for i in range(d_size)]
    qa_names = [st.text_input(f"QA {i+1}", f"Tester {i+1}", key=f"qn_{i}") for i in range(q_size)]
    uploaded_file = st.file_uploader("Upload Backlog")

# --- Main Dashboard ---
if uploaded_file:
    df_raw = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    final_plan = run_architect_allocation(df_raw, dev_names, qa_names, splits)
    
    tabs = st.tabs(["🚀 Phase Timeline", "⚖️ Scope Negotiator", "📊 Load Chart"])

    with tabs[0]:
        for i in range(5):
            s_name = f"Sprint {i}"
            s_data = final_plan[final_plan['Sprint'] == s_name]
            res_sum = s_data.groupby('Owner')['Hours'].sum()
            overloaded = res_sum[res_sum > max_cap]
            
            with st.expander(f"{s_name} | {'⚠️ OVERLOAD' if not overloaded.empty else '✅ OK'}"):
                st.write(f"**Max Capacity: {max_cap}h**")
                cols = st.columns(len(res_sum))
                for idx, (owner, hrs) in enumerate(res_sum.items()):
                    with cols[idx]:
                        st.metric(owner, f"{hrs}h", f"{hrs-max_cap}h Over" if hrs > max_cap else None, delta_color="inverse")
                st.dataframe(s_data[['Task', 'Owner', 'Hours']], use_container_width=True, hide_index=True)

    with tabs[1]:
        st.header("Scope Negotiation Console")
        res_sum_total = final_plan.groupby(['Sprint', 'Owner'])['Hours'].sum()
        critical_sprints = res_sum_total[res_sum_total > max_cap].index.get_level_values(0).unique()
        
        if len(critical_sprints) > 0:
            st.warning(f"Overload detected in: {', '.join(critical_sprints)}")
            if st.button("AI Suggest: Descope to Future Release"):
                # Strategy: Move the last dev task of the most overloaded sprint
                target_sprint = critical_sprints[0]
                task_to_move = final_plan[(final_plan['Sprint'] == target_sprint) & (final_plan['Role'] == 'Dev')].iloc[-1]['Task']
                st.session_state.future_release.append(task_to_move)
                st.success(f"Moved '{task_to_move}' to Future Release.")
                st.rerun()
        else:
            st.success("Scope is currently within capacity limits.")
            
        if st.session_state.future_release:
            st.subheader("Future Release Bucket")
            st.write(st.session_state.future_release)
            if st.button("Reset Scope"):
                st.session_state.future_release = []
                st.rerun()

else:
    st.info("Jarvis: Please upload your backlog to start scope negotiation.")
