import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Jarvis Audit & Ingest", layout="wide")

# --- Session State for Audit ---
if 'audit_log' not in st.session_state:
    st.session_state.audit_log = []

# --- Validation Logic ---
REQUIRED_INPUTS = [
    "Analysis Phase", "Development Phase", "Code Review", "Bug Fixes",
    "TC preparation", "QA testing", "Bug retest", "Integration testing",
    "Merge and Deploy", "Smoke test"
]

def validate_excel(df, filename):
    missing = [col for col in REQUIRED_INPUTS if col not in df.columns]
    timestamp = datetime.now().strftime("%H:%M:%S")
    if missing:
        error_msg = f"required {missing} inputs missing"
        st.session_state.audit_log.insert(0, {"Time": timestamp, "File": filename, "Status": "❌ Failed", "Detail": error_msg})
        return False, missing
    st.session_state.audit_log.insert(0, {"Time": timestamp, "File": filename, "Status": "✅ Success", "Detail": "All headers validated"})
    return True, []

# --- Core Allocation Logic ---
def run_allocation(dev_names, qa_names, data, max_cap):
    plan = []
    all_roles = dev_names + qa_names + ["Lead", "DevOps"]
    resource_load = {f"Sprint {i}": {name: 0 for name in all_roles} for i in range(5)}
    
    def assign(sprint, names, task, role, hrs):
        owner = min(names, key=lambda x: resource_load[sprint][x])
        resource_load[sprint][owner] += hrs
        return {"Sprint": sprint, "Task": task, "Owner": owner, "Role": role, "Hours": hrs}

    # S0: Analysis
    plan.append(assign("Sprint 0", ["Lead"], "Analysis Phase", "Lead", data["Analysis Phase"]))
    
    dev_split = data["Development Phase"] / 2
    rev_split = data["Code Review"] / 2
    
    for s in ["Sprint 1", "Sprint 2"]:
        if s == "Sprint 1":
            plan.append(assign(s, qa_names, "TC Preparation", "QA", data["TC preparation"]))
        for d in dev_names:
            plan.append(assign(s, [d], "Development", "Dev", dev_split / len(dev_names)))
        plan.append(assign(s, ["Lead"], "Code Review", "Lead", rev_split))

    # S3: Testing
    plan.append(assign("Sprint 3", qa_names, "QA Testing", "QA", data["QA testing"]))
    plan.append(assign("Sprint 3", qa_names, "Integration Testing", "QA", data["Integration testing"]))

    # S4: Launch
    plan.append(assign("Sprint 4", dev_names, "Bug Fixes", "Dev", data["Bug Fixes"]))
    plan.append(assign("Sprint 4", qa_names, "Bug retest", "QA", data["Bug retest"]))
    plan.append(assign("Sprint 4", ["DevOps"], "Merge and Deploy", "Ops", data["Merge and Deploy"]))
    plan.append(assign("Sprint 4", qa_names, "Smoke test", "QA", data["Smoke test"]))
    
    return pd.DataFrame(plan)

# --- Sidebar ---
with st.sidebar:
    st.header("📂 Data Source")
    uploaded_file = st.file_uploader("Upload Phase Excel", type=["xlsx", "csv"])
    
    if st.session_state.audit_log:
        st.subheader("📜 Validation Log")
        st.dataframe(pd.DataFrame(st.session_state.audit_log), hide_index=True)

    st.divider()
    st.header("👥 Team")
    total_size = st.number_input("Total Team Size", 1, 50, 5)
    d_count = st.number_input("Dev Team Size", 1, total_size, 3)
    q_count = st.number_input("QA Team Size", 1, total_size - d_count, 1)
    
    dev_names = [st.text_input(f"Dev {i+1}", f"D{i+1}", key=f"d_{i}") for i in range(d_count)]
    qa_names = [st.text_input(f"QA {i+1}", f"Q{i+1}", key=f"q_{i}") for i in range(q_count)]

    st.divider()
    sprint_days = st.number_input("Sprint Days", 1, 30, 10)
    daily_hrs = st.slider("Daily Hours", 4, 12, 8)
    max_cap = sprint_days * daily_hrs

# --- Data Ingest ---
current_data = None

if uploaded_file:
    df_input = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    is_valid, missing = validate_excel(df_input, uploaded_file.name)
    if not is_valid:
        st.error(f"required {missing} inputs missing")
    else:
        st.success(f"Validated: {uploaded_file.name}")
        current_data = df_input.iloc[0].to_dict()
else:
    st.info("Manual Entry Mode")
    c1, c2 = st.columns(2)
    with c1:
        h_ana = st.number_input("Analysis Phase", 0, 500, 40)
        h_dev = st.number_input("Development Phase", 0, 2000, 240)
        h_rev = st.number_input("Code Review", 0, 500, 40)
        h_tc = st.number_input("TC preparation", 0, 500, 30)
        h_qa = st.number_input("QA testing", 0, 1000, 80)
    with c2:
        h_int = st.number_input("Integration testing", 0, 500, 40)
        h_fix = st.number_input("Bug Fixes", 0, 500, 40)
        h_ret = st.number_input("Bug retest", 0, 500, 20)
        h_dep = st.number_input("Merge and Deploy", 0, 500, 16)
        h_smo = st.number_input("Smoke test", 0, 500, 8)
    
    current_data = {
        "Analysis Phase": h_ana, "Development Phase": h_dev, "Code Review": h_rev,
        "TC preparation": h_tc, "QA testing": h_qa, "Integration testing": h_int,
        "Bug Fixes": h_fix, "Bug retest": h_ret, "Merge and Deploy": h_dep, "Smoke test": h_smo
    }

# --- Dashboard ---
if current_data:
    final_plan = run_allocation(dev_names, qa_names, current_data, max_cap)
    
    tabs = st.tabs(["🚀 Phase Roadmap", "📉 Efficiency Matrix"])
    
    with tabs[0]:
        for i in range(5):
            s_name = f"Sprint {i}"
            s_data = final_plan[final_plan['Sprint'] == s_name].copy()
            s_data['Utilization %'] = (s_data['Hours'] / max_cap) * 100
            with st.expander(f"{s_name} Breakdown"):
                st.dataframe(s_data.style.format({'Utilization %': '{:.1f}%'}), use_container_width=True, hide_index=True)

    with tabs[1]:
        load_df = final_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
        load_df['Utilization %'] = (load_df['Hours'] / max_cap) * 100
        st.plotly_chart(px.bar(load_df, x="Sprint", y="Utilization %", color="Owner", barmode="group", title="Resource Loading %"))
