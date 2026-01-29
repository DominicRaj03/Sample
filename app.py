import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# Dependency check for Excel export
try:
    import xlsxwriter
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

st.set_page_config(page_title="Jarvis Reporting Architect", layout="wide")

# --- 1. Persistent Memory ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'sprint_caps' not in st.session_state:
    st.session_state.sprint_caps = {}
if 'project_dates' not in st.session_state:
    st.session_state.project_dates = {"Start": None, "End": None}

# --- 2. Allocation Logic ---
def run_sequential_allocation(dev_names, qa_names, lead_names, data, base_cap, num_sprints, start_date, sprint_days, daily_hrs, buffer_pct):
    generated_plan = []
    sprint_list = [f"Sprint {i}" for i in range(num_sprints)]
    all_staff = dev_names + qa_names + lead_names + ["DevOps"]
    resource_load = {s: {name: 0 for name in all_staff} for s in sprint_list}
    sprint_caps = {}
    sprint_metadata = {}

    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days - 1)
        cap = max((base_cap) * (1 - (buffer_pct / 100)), 0.1)
        
        s_label = f"Sprint {i}"
        sprint_caps[s_label] = cap
        sprint_metadata[s_label] = {"Start": s_start.strftime('%Y-%m-%d'), "End": s_end.strftime('%Y-%m-%d')}

        def assign(sprint, names, task, role, hrs):
            owner = min(names, key=lambda x: resource_load[sprint][x])
            resource_load[sprint][owner] += hrs
            return {
                "Sprint": sprint, "Start Date": sprint_metadata[sprint]["Start"],
                "End Date": sprint_metadata[sprint]["End"], "Status": "Not Started",
                "Task": task, "Owner": owner, "Role": role, "Hours": float(hrs)
            }

        if i == 0:
            generated_plan.append(assign(s_label, lead_names, "Analysis Phase", "Lead", data["Analysis"]))
            generated_plan.append(assign(s_label, qa_names, "TC preparation", "QA", data["TC_Prep"]))
        elif 0 < i < (num_sprints - 1):
            div = max(1, num_sprints - 2)
            generated_plan.append(assign(s_label, dev_names, "Development Phase", "Dev", data["Dev"]/div))
            generated_plan.append(assign(s_label, lead_names, "Code Review", "Lead", data["Review"]/div))
            generated_plan.append(assign(s_label, qa_names, "QA testing", "QA", data["QA_Test"]/div))
            generated_plan.append(assign(s_label, qa_names, "Integration Testing", "QA", data["Integ"]/div))
        elif i == (num_sprints - 1):
            generated_plan.append(assign(s_label, dev_names, "Bug Fixes", "Dev", data["Fixes"]))
            generated_plan.append(assign(s_label, qa_names, "Bug retest", "QA", data["Retest"]))
            generated_plan.append(assign(s_label, qa_names, "Smoke test", "QA", data["Smoke"]))
            generated_plan.append(assign(s_label, ["DevOps"], "Merge and Deploy", "Ops", data["Deploy"]))

    return pd.DataFrame(generated_plan), sprint_caps, sprint_metadata, start_date, start_date + timedelta(days=num_sprints * sprint_days - 1)

# --- 3. Sidebar ---
with st.sidebar:
    st.header("👥 Team Configuration")
    c_d, c_q, c_l = st.columns(3)
    d_count = c_d.number_input("Devs", 1, 20, 3); q_count = c_q.number_input("QA", 1, 20, 1); l_count = c_l.number_input("Leads", 1, 10, 1)
    st.divider()
    dev_names = [st.text_input(f"Dev {i+1}", f"D{i+1}", key=f"d_{i}") for i in range(d_count)]
    qa_names = [st.text_input(f"QA {i+1}", f"Q{i+1}", key=f"q_{i}") for i in range(q_count)]
    lead_names = [st.text_input(f"Lead {i+1}", f"L{i+1}", key=f"l_{i}") for i in range(l_count)]
    st.divider()
    st.header("📅 Timeline Settings")
    start_date_input = st.date_input("Start Date", datetime(2026, 2, 9))
    num_sprints = st.selectbox("Total Sprints", range(2, 11), index=3)
    sprint_days = st.number_input("Sprint Days", 1, 30, 14); daily_hrs = st.slider("Daily Hrs/Person", 4, 12, 8); buffer_pct = st.slider("Buffer (%)", 0, 50, 10)

# --- 4. Main UI ---
st.title("Jarvis Phase-Gate Manager")

with st.expander("📥 Effort Baseline (Unrestricted)", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        analysis = st.number_input("Analysis Phase", value=25.0); dev_h = st.number_input("Development Phase", value=150.0)
        fixes = st.number_input("Bug Fixes", value=30.0); review = st.number_input("Code Review", value=20.0)
    with col2:
        qa_h = st.number_input("QA testing", value=80.0); tc_p = st.number_input("TC preparation", value=40.0)
        retest = st.number_input("Bug retest", value=15.0); integ = st.number_input("Integration Testing", value=20.0)
        smoke = st.number_input("Smoke test", value=8.0); deploy = st.number_input("Merge and Deploy", value=6.0)

if st.button("🚀 GENERATE INITIAL PLAN", type="primary", use_container_width=True):
    inputs = {"Analysis": analysis, "Dev": dev_h, "Fixes": fixes, "Review": review, "QA_Test": qa_h, 
              "TC_Prep": tc_p, "Retest": retest, "Integ": integ, "Smoke": smoke, "Deploy": deploy}
    plan, caps, meta, p_start, p_end = run_sequential_allocation(dev_names, qa_names, lead_names, inputs, sprint_days*daily_hrs, num_sprints, start_date_input, sprint_days, daily_hrs, buffer_pct)
    st.session_state.master_plan = plan
    st.session_state.sprint_caps = caps; st.session_state.sprint_meta = meta; st.session_state.project_dates = {"Start": p_start, "End": p_end}
    st.rerun()

# --- 5. Visual Analytics & Reporting ---
if st.session_state.master_plan is not None:
    # Capacity Gauge
    total_hours = st.session_state.master_plan['Hours'].sum()
    total_cap = sum(st.session_state.sprint_caps.values()) * (d_count + q_count + l_count)
    util_pct = (total_hours / total_cap) * 100
    gauge_fig = go.Figure(go.Indicator(mode="gauge+number", value=util_pct, title={'text': "Total Project Capacity Utilization (%)"},
                                      gauge={'axis': {'range': [None, 120]}, 'bar': {'color': "red" if util_pct > 100 else "green"}}))
    st.plotly_chart(gauge_fig, use_container_width=True)

    v1, v2 = st.columns(2)
    with v1:
        st.subheader("📊 Workload by Resource")
        util_fig = px.bar(st.session_state.master_plan, x="Sprint", y="Hours", color="Owner", barmode="group", text_auto='.1f')
        st.plotly_chart(util_fig, use_container_width=True)
    with v2:
        st.subheader("🔥 Sprint Status Heatmap")
        status_counts = st.session_state.master_plan.groupby(['Sprint', 'Status']).size().reset_index(name='Task Count')
        heat_fig = px.density_heatmap(status_counts, x="Sprint", y="Status", z="Task Count", color_continuous_scale="Viridis", text_auto=True)
        st.plotly_chart(heat_fig, use_container_width=True)

    st.subheader("📝 Roadmap Editor")
    st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True, key="master_edit",
                                                 column_config={"Status": st.column_config.SelectboxColumn("Status", options=["Not Started", "In Progress", "Completed"])})

    # Export Logic
    if EXCEL_SUPPORT:
        st.divider()
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            st.session_state.master_plan.to_excel(writer, index=False, sheet_name="Roadmap")
            # Summary Sheet
            summ = st.session_state.master_plan.groupby('Sprint').agg({'Hours': 'sum'}).reset_index()
            summ.to_excel(writer, index=False, sheet_name="Sprint_Summary")
        st.download_button("📥 EXPORT FULL REPORT TO EXCEL", data=buf.getvalue(), file_name=f"Jarvis_Roadmap_{datetime.now().strftime('%Y%m%d')}.xlsx", type="secondary")

if st.button("🗑️ Reset All"):
    st.session_state.master_plan = None
    st.rerun()
