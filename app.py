import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Phase Architect", layout="wide")

# --- Session State ---
if 'manual_overrides' not in st.session_state:
    st.session_state.manual_overrides = {}
if 'resource_away' not in st.session_state:
    st.session_state.resource_away = {}

# --- Logic Core ---
def run_phase_allocation(dev_names, qa_names, splits):
    plan = []
    # Capacity Tracking
    resource_load = {f"Sprint {i}": {name: 0 for name in dev_names + qa_names + ["Lead", "Designer", "DevOps"]} for i in range(5)}

    def assign_work(sprint, names, task_name, role, hours):
        ov_key = f"{sprint}_{task_name}"
        if ov_key in st.session_state.manual_overrides:
            owner = st.session_state.manual_overrides[ov_key]
        else:
            avail = [n for n in names if not st.session_state.resource_away.get(f"{sprint}_{n}", False)]
            owner = min(avail, key=lambda x: resource_load[sprint][x]) if avail else names[0]
        
        resource_load[sprint][owner] += hours
        return {"Sprint": sprint, "Task": task_name, "Owner": owner, "Role": role, "Hours": hours}

    # Sprint 0: Analysis
    plan.append(assign_work("Sprint 0", ["Lead"], "Analysis Phase", "Lead", splits['Analysis']))
    
    # Sprints 1 & 2: Development & Review
    # Splitting the total dev hours across two sprints
    dev_per_sprint = splits['TotalDev'] / 2
    review_per_sprint = splits['CodeReview'] / 2
    
    for s in ["Sprint 1", "Sprint 2"]:
        # Assign Dev Hours
        for d_name in dev_names:
            plan.append(assign_work(s, [d_name], f"Dev Work: {d_name}", "Dev", dev_per_sprint / len(dev_names)))
        # Assign Code Review (distributed among devs)
        for d_name in dev_names:
            plan.append(assign_work(s, [d_name], f"Code Review: {d_name}", "Dev", review_per_sprint / len(dev_names)))

    # Sprint 3: QA Execution
    plan.append(assign_work("Sprint 3", qa_names, "QA Phase", "QA", splits['QA']))

    # Sprint 4: Stabilization & Deployment
    plan.append(assign_work("Sprint 4", dev_names, "Bug Fixes", "Dev", splits['BugFixes']))
    plan.append(assign_work("Sprint 4", qa_names, "Bug Retest", "QA", splits['BugRetest']))
    plan.append(assign_work("Sprint 4", ["DevOps"], "Merge & Deployment", "Ops", splits['MergeDeploy']))
    
    return pd.DataFrame(plan)

# --- Sidebar: Phase Inputs ---
with st.sidebar:
    st.header("⚙️ Project Effort (Hours)")
    s_analysis = st.number_input("Analysis (S0)", 0, 500, 40)
    s_dev = st.number_input("Development Total", 0, 2000, 200)
    s_review = st.number_input("Code Review Total", 0, 500, 40)
    s_qa = st.number_input("QA Total", 0, 1000, 80)
    s_fixes = st.number_input("Bug Fixes (Last Sprint)", 0, 500, 40)
    s_retest = st.number_input("Bug Retest (Last Sprint)", 0, 500, 20)
    s_merge = st.number_input("Merge & Deploy (Final)", 0, 500, 16)
    
    st.divider()
    sprint_days = st.number_input("Sprint Days", 1, 30, 12)
    daily_hrs = st.slider("Daily Hours", 4, 12, 8)
    max_cap = sprint_days * daily_hrs

    st.header("👥 Team")
    dev_names = [st.text_input(f"Dev {i+1}", f"Dev {i+1}", key=f"dn_{i}") for i in range(2)]
    qa_names = [st.text_input(f"QA {i+1}", f"Tester {i+1}", key=f"qn_{i}") for i in range(1)]

# --- Main App ---
splits = {
    'Analysis': s_analysis, 'TotalDev': s_dev, 'CodeReview': s_review,
    'QA': s_qa, 'BugFixes': s_fixes, 'BugRetest': s_retest, 'MergeDeploy': s_merge
}

final_plan = run_phase_allocation(dev_names, qa_names, splits)

# UI Visibility
tabs = st.tabs(["📊 Sprint Roadmap", "🌡️ Resource Stress", "📋 Phase Breakdown"])

with tabs[0]:
    for i in range(5):
        s_name = f"Sprint {i}"
        s_data = final_plan[final_plan['Sprint'] == s_name]
        total_h = s_data['Hours'].sum()
        
        with st.expander(f"📅 {s_name} Overview | Total: {total_h:.1f} hrs"):
            res_sum = s_data.groupby('Owner')['Hours'].sum()
            cols = st.columns(len(res_sum))
            for idx, (owner, h) in enumerate(res_sum.items()):
                color = "red" if h > max_cap else "green"
                cols[idx].metric(owner, f"{h:.1f}h", f"{h-max_cap:.1f}h" if h > max_cap else None, delta_color="inverse")
            st.dataframe(s_data[['Task', 'Owner', 'Hours', 'Role']], hide_index=True, use_container_width=True)

with tabs[1]:
    st.header("Team Utilization Heatmap")
    load_df = final_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
    fig = px.bar(load_df, x="Sprint", y="Hours", color="Owner", barmode="group")
    fig.add_hline(y=max_cap, line_dash="dash", line_color="red", annotation_text="Max Capacity")
    st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.header("Phase Effort Distribution")
    phase_summary = pd.DataFrame(list(splits.items()), columns=['Phase', 'Hours'])
    st.table(phase_summary)
