import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Jarvis Efficiency Architect", layout="wide")

# --- Session State ---
if 'leave_registry' not in st.session_state:
    st.session_state.leave_registry = []

# --- Logic Core ---
def run_phase_allocation(dev_names, qa_names, splits, apply_buffer, enable_delegation, backup_dev):
    plan = []
    all_roles = dev_names + qa_names + ["Lead", "Designer", "DevOps"]
    resource_load = {f"Sprint {i}": {name: 0 for name in all_roles} for i in range(5)}
    multiplier = 1.10 if apply_buffer else 1.0
    
    def assign_work(sprint, names, task_name, role, hours):
        owner = min(names, key=lambda x: resource_load[sprint][x])
        buffered_hours = hours * multiplier
        resource_load[sprint][owner] += buffered_hours
        return {"Sprint": sprint, "Task": task_name, "Owner": owner, "Role": role, "Hours": buffered_hours}

    # S0: Analysis
    plan.append(assign_work("Sprint 0", ["Lead"], "Analysis Phase", "Lead", splits['Analysis']))
    
    # S1 & S2: Dev & Review
    dev_per_sprint = splits['TotalDev'] / 2
    review_per_sprint = splits['CodeReview'] / 2
    
    for s in ["Sprint 1", "Sprint 2"]:
        if s == "Sprint 1":
            plan.append(assign_work(s, qa_names, "Test Prep", "QA", splits['QA'] * 0.20))
        for d_name in dev_names:
            plan.append(assign_work(s, [d_name], f"Dev Work", "Dev", dev_per_sprint / len(dev_names)))
        
        limit = (st.session_state.base_days * 8) * (st.session_state.workload_cap_pct / 100)
        if enable_delegation and (resource_load[s]["Lead"] + (review_per_sprint * multiplier) > limit):
            plan.append(assign_work(s, [backup_dev], "Delegated Review", "Backup Lead", review_per_sprint))
        else:
            plan.append(assign_work(s, ["Lead"], "Lead Review", "Lead", review_per_sprint))

    # S3 & S4
    plan.append(assign_work("Sprint 3", qa_names, "QA Execution", "QA", splits['QA'] * 0.80))
    plan.append(assign_work("Sprint 4", dev_names, "Bug Fixes", "Dev", splits['BugFixes']))
    plan.append(assign_work("Sprint 4", qa_names, "Bug Retest", "QA", splits['BugRetest']))
    plan.append(assign_work("Sprint 4", ["DevOps"], "Deployment", "Ops", splits['MergeDeploy']))
    
    return pd.DataFrame(plan)

# --- Sidebar ---
with st.sidebar:
    st.header("👥 Team & Velocity")
    total_team = st.number_input("Total Team Size", 1, 50, 5)
    d_count = st.number_input("Dev Count", 1, total_team, 3)
    q_count = st.number_input("QA Count", 1, total_team, 1)
    dev_names = [st.text_input(f"Dev {i+1}", f"D{i+1}", key=f"dn_{i}") for i in range(d_count)]
    qa_names = [st.text_input(f"QA {i+1}", f"Q{i+1}", key=f"qn_{i}") for i in range(q_count)]
    
    st.divider()
    pts_ratio = st.slider("Hours per Story Point", 2, 16, 6)
    
    st.divider()
    st.header("⚙️ Controls")
    st.session_state.base_days = st.number_input("Sprint Days", 1, 30, 12)
    st.session_state.workload_cap_pct = st.slider("Workload Cap (%)", 50, 100, 90)
    backup_dev = st.selectbox("Lead Backup", options=dev_names)
    enable_delegation = st.toggle("Auto-Delegate", value=True)
    apply_buffer = st.toggle("Apply 10% Buffer", value=False)

# --- Dashboard ---
splits = {'Analysis': 40, 'TotalDev': 240, 'CodeReview': 60, 'QA': 100, 'BugFixes': 40, 'BugRetest': 20, 'MergeDeploy': 16}
final_plan = run_phase_allocation(dev_names, qa_names, splits, apply_buffer, enable_delegation, backup_dev)

t1, t2 = st.tabs(["📊 Efficiency Matrix", "📋 Sprint Details"])

with t1:
    st.header("Sprint Efficiency: Hours vs Story Points")
    
    # Calculate Metrics
    metrics = []
    for s in [f"Sprint {i}" for i in range(5)]:
        s_data = final_plan[final_plan['Sprint'] == s]
        total_hrs = s_data['Hours'].sum()
        # Points only come from Dev/QA specific tasks
        points = s_data[s_data['Role'].isin(['Dev', 'QA', 'Backup Lead'])]['Hours'].sum() / pts_ratio
        efficiency = (points * pts_ratio) / total_hrs if total_hrs > 0 else 0
        metrics.append({"Sprint": s, "Total Hours": round(total_hrs, 1), "Story Points": round(points, 1), "Efficiency %": round(efficiency*100, 1)})
    
    eff_df = pd.DataFrame(metrics)
    st.table(eff_df)
    
    # Dual Axis Chart
    fig = px.bar(eff_df, x="Sprint", y="Total Hours", title="Resource Hours vs Output Points", text_auto=True)
    fig.add_scatter(x=eff_df["Sprint"], y=eff_df["Story Points"], name="Story Points", yaxis="y2", marker=dict(color="red"))
    fig.update_layout(yaxis2=dict(title="Story Points", overlaying="y", side="right"))
    st.plotly_chart(fig, use_container_width=True)

with t2:
    for i in range(5):
        s_name = f"Sprint {i}"
        st.expander(s_name).dataframe(final_plan[final_plan['Sprint'] == s_name], use_container_width=True, hide_index=True)
