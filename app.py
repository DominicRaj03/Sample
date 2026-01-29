import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

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

# --- Logic Core ---
def run_balanced_allocation(df, dev_names, qa_names):
    task_col = next((c for c in df.columns if "Task" in c), df.columns[1])
    hour_col = next((c for c in df.columns if "Hours" in c or "Effort" in c), df.columns[-1])
    
    local_df = df.copy()
    local_df[hour_col] = pd.to_numeric(local_df[hour_col], errors='coerce').fillna(0)
    dev_tasks = local_df.to_dict('records')
    
    plan = []
    resource_load = {f"Sprint {i}": {name: 0 for name in dev_names + qa_names + ["Designer", "DevOps"]} for i in range(5)}

    def assign_to_least_loaded(sprint, names, task_name, role, hours):
        override_key = f"{sprint}_{task_name}"
        if override_key in st.session_state.manual_overrides:
            assigned_owner = st.session_state.manual_overrides[override_key]
        else:
            available = [n for n in names if not st.session_state.resource_away.get(f"{sprint}_{n}", False)]
            assigned_owner = min(available, key=lambda x: resource_load[sprint][x]) if available else names[0]
        
        resource_load[sprint][assigned_owner] += hours
        return {"Sprint": sprint, "Task": task_name, "Owner": assigned_owner, "Role": role, "Hours": hours}

    # Sprint 0
    plan.append(assign_to_least_loaded("Sprint 0", [dev_names[0]], "SRS Documentation", "Dev", 20))
    plan.append({"Sprint": "Sprint 0", "Task": "UI/UX Mockups", "Owner": "Designer", "Role": "Design", "Hours": 40})

    half = len(dev_tasks) // 2
    # Sprint 1
    for task in dev_tasks[:half]:
        plan.append(assign_to_least_loaded("Sprint 1", dev_names, task[task_col], "Dev", task[hour_col]))
    plan.append(assign_to_least_loaded("Sprint 1", qa_names, "QA: Test Mapping", "QA", 15))

    # Sprint 2
    for task in dev_tasks[half:]:
        plan.append(assign_to_least_loaded("Sprint 2", dev_names, task[task_col], "Dev", task[hour_col]))
    plan.append(assign_to_least_loaded("Sprint 2", qa_names, "QA: Execute Sprint 1", "QA", 25))

    # Sprint 3
    plan.append(assign_to_least_loaded("Sprint 3", qa_names, "QA: Execute Sprint 2", "QA", 25))
    for i, bug in enumerate(st.session_state.defects):
        plan.append(assign_to_least_loaded("Sprint 3", dev_names, f"FIX: {bug['title']}", "Dev", 4))

    # Sprint 4
    plan.append({"Sprint": "Sprint 4", "Task": "Final Deployment", "Owner": "DevOps", "Role": "Ops", "Hours": 10})
    
    return pd.DataFrame(plan)

# --- Sidebar ---
with st.sidebar:
    st.header("👥 Team & Timeline")
    d_size = st.number_input("Dev Team Size", 1, 10, 2)
    q_size = st.number_input("QA Team Size", 1, 10, 1)
    dev_names = [st.text_input(f"Dev {i+1}", f"Developer {i+1}", key=f"dn_{i}") for i in range(d_size)]
    qa_names = [st.text_input(f"QA {i+1}", f"Tester {i+1}", key=f"qn_{i}") for i in range(q_size)]
    st.divider()
    start_date = st.date_input("Project Kick-off", datetime(2026, 1, 27))
    uploaded_file = st.file_uploader("Upload Backlog", type=['xlsx', 'csv'])

# --- Main Logic ---
if uploaded_file:
    df_raw = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    final_plan = run_balanced_allocation(df_raw, dev_names, qa_names)

    tabs = st.tabs(["🚀 Sprint Visibility", "🌴 Availability", "🔄 Manual Override", "🏁 Status Update"])

    with tabs[0]:
        st.header("Executive Sprint Overview")
        for i in range(5):
            s_name = f"Sprint {i}"
            s_start = start_date + timedelta(days=i*14)
            s_end = s_start + timedelta(days=13)
            s_data = final_plan[final_plan['Sprint'] == s_name]
            total_hrs = s_data['Hours'].sum()
            
            with st.expander(f"📅 {s_name}: {s_start.strftime('%b %d')} - {s_end.strftime('%b %d')} | Total: {total_hrs} hrs", expanded=(i==1)):
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.write("**Resource Hours:**")
                    res_breakdown = s_data.groupby('Owner')['Hours'].sum()
                    for owner, hrs in res_breakdown.items():
                        st.write(f"- {owner}: `{hrs} hrs`")
                with c2:
                    st.dataframe(s_data[['Task', 'Owner', 'Hours']], hide_index=True, use_container_width=True)

    with tabs[1]:
        st.header("Availability Matrix")
        all_m = dev_names + qa_names
        for s in range(5):
            cols = st.columns(len(all_m))
            for idx, m in enumerate(all_m):
                key = f"Sprint {s}_{m}"
                with cols[idx]:
                    if not st.checkbox(f"{m} (S{s})", value=not st.session_state.resource_away.get(key, False), key=f"avail_{key}"):
                        st.session_state.resource_away[key] = True
                    else:
                        st.session_state.resource_away[key] = False

    with tabs[2]:
        st.header("Resource Swap")
        s_sel = st.selectbox("Sprint:", [f"Sprint {i}" for i in range(5)])
        for _, row in final_plan[final_plan['Sprint'] == s_sel].iterrows():
            c1, c2 = st.columns([3, 1])
            with c1: st.write(f"{row['Task']} ({row['Hours']}h)")
            with c2:
                eligible = dev_names if row['Role'] == "Dev" else qa_names if row['Role'] == "QA" else [row['Owner']]
                choice = st.selectbox("Owner:", eligible, key=f"sw_{s_sel}_{row['Task']}", index=eligible.index(row['Owner']) if row['Owner'] in eligible else 0)
                if choice != row['Owner']:
                    st.session_state.manual_overrides[f"{s_sel}_{row['Task']}"] = choice
                    st.rerun()

    with tabs[3]:
        s_curr = st.selectbox("Update Tracker:", [f"Sprint {i}" for i in range(5)])
        for _, row in final_plan[final_plan['Sprint'] == s_curr].iterrows():
            st.checkbox(f"[{row['Owner']}] {row['Task']} ({row['Hours']}h)", key=f"track_{s_curr}_{row['Task']}")
else:
    st.info("Jarvis: Awaiting data to generate the Sprint Visibility timeline.")
