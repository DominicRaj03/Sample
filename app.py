import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

# Dependency check for Excel
try:
    import xlsxwriter
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

st.set_page_config(page_title="Jarvis Temporal Resource Architect", layout="wide")

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
        sprint_metadata[s_label] = {
            "Start": s_start.strftime('%Y-%m-%d'),
            "End": s_end.strftime('%Y-%m-%d'),
            "Range": f"{s_start.strftime('%b %d')} - {s_end.strftime('%b %d')}"
        }

        def assign(sprint, names, task, role, hrs):
            owner = min(names, key=lambda x: resource_load[sprint][x])
            resource_load[sprint][owner] += hrs
            return {
                "Sprint": sprint, 
                "Start Date": sprint_metadata[sprint]["Start"],
                "End Date": sprint_metadata[sprint]["End"],
                "Status": "Not Started",
                "Task": task, 
                "Owner": owner, 
                "Role": role, 
                "Hours": float(hrs)
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

    final_end = start_date + timedelta(days=num_sprints * sprint_days - 1)
    return pd.DataFrame(generated_plan), sprint_caps, sprint_metadata, start_date, final_end

# --- 3. Sidebar ---
with st.sidebar:
    st.header("👥 Team List")
    d_names = [st.text_input(f"Dev {i+1}", f"D{i+1}", key=f"d_{i}") for i in range(3)]
    q_names = [st.text_input(f"QA {i+1}", f"Q{i+1}", key=f"q_{i}") for i in range(1)]
    l_names = [st.text_input(f"Lead {i+1}", f"L{i+1}", key=f"l_{i}") for i in range(1)]
    st.divider()
    st.header("📅 Timeline Settings")
    start_date_input = st.date_input("Project Start Date", datetime(2026, 2, 9))
    num_sprints = st.selectbox("Total Sprints", range(2, 11), index=3)
    sprint_days = st.number_input("Days per Sprint", 1, 30, 14)
    daily_hrs = st.slider("Daily Hours", 4, 12, 8)
    buffer_pct = st.slider("Buffer (%)", 0, 50, 10)
    max_cap_base = sprint_days * daily_hrs

# --- 4. Main UI ---
st.title("Jarvis Phase-Gate Manager")

if st.session_state.project_dates["Start"] is not None:
    st.subheader("📅 Project Overview")
    ov1, ov2, ov3 = st.columns(3)
    ov1.metric("Project Start", st.session_state.project_dates["Start"].strftime('%Y-%m-%d'))
    ov2.metric("Project End", st.session_state.project_dates["End"].strftime('%Y-%m-%d'))
    ov3.metric("Total Window", f"{(st.session_state.project_dates['End'] - st.session_state.project_dates['Start']).days} Days")
    st.divider()

with st.expander("📥 Effort Baseline"):
    c1, c2 = st.columns(2)
    with c1:
        analysis = st.number_input("Analysis Phase", 25.0); dev = st.number_input("Development Phase", 150.0)
        fixes = st.number_input("Bug Fixes", 30.0); review = st.number_input("Code Review", 20.0)
    with c2:
        qa_t = st.number_input("QA testing", 80.0); tc_p = st.number_input("TC preparation", 40.0)
        retest = st.number_input("Bug retest", 15.0); integ = st.number_input("Integration Testing", 20.0)
        smoke = st.number_input("Smoke test", 8.0); deploy = st.number_input("Merge and Deploy", 6.0)

if st.button("🚀 GENERATE INITIAL PLAN", type="primary", use_container_width=True):
    inputs = {"Analysis": analysis, "Dev": dev, "Fixes": fixes, "Review": review, "QA_Test": qa_t, 
              "TC_Prep": tc_p, "Retest": retest, "Integ": integ, "Smoke": smoke, "Deploy": deploy}
    plan, caps, meta, p_start, p_end = run_sequential_allocation(d_names, q_names, l_names, inputs, max_cap_base, num_sprints, start_date_input, sprint_days, daily_hrs, buffer_pct)
    st.session_state.master_plan = plan
    st.session_state.sprint_caps = caps
    st.session_state.sprint_meta = meta
    st.session_state.project_dates = {"Start": p_start, "End": p_end}
    st.rerun()

# --- 5. Summary & Editor ---
if st.session_state.master_plan is not None:
    st.subheader("📋 Sprint Dates & Capacity")
    summary = st.session_state.master_plan.groupby('Sprint').agg({'Hours': 'sum'}).reset_index()
    summary['Start Date'] = summary['Sprint'].apply(lambda x: st.session_state.sprint_meta[x]['Start'])
    summary['End Date'] = summary['Sprint'].apply(lambda x: st.session_state.sprint_meta[x]['End'])
    summary['Capacity'] = summary['Sprint'].map(st.session_state.sprint_caps)
    summary['Utilization'] = (summary['Hours'] / summary['Capacity'] * 100).round(1).astype(str) + '%'
    st.table(summary[['Sprint', 'Start Date', 'End Date', 'Hours', 'Capacity', 'Utilization']])

    st.subheader("📝 Roadmap Editor & Filter")
    f1, f2 = st.columns(2)
    with f1:
        owner_filter = st.multiselect("Filter by Owner", options=st.session_state.master_plan['Owner'].unique(), default=st.session_state.master_plan['Owner'].unique())
    with f2:
        role_filter = st.multiselect("Filter by Role", options=st.session_state.master_plan['Role'].unique(), default=st.session_state.master_plan['Role'].unique())
    
    display_df = st.session_state.master_plan[
        (st.session_state.master_plan['Owner'].isin(owner_filter)) & 
        (st.session_state.master_plan['Role'].isin(role_filter))
    ].copy()

    st.session_state.master_plan = st.data_editor(
        display_df,
        use_container_width=True,
        key="main_editor",
        column_config={
            "Start Date": st.column_config.TextColumn("Start Date", disabled=True),
            "End Date": st.column_config.TextColumn("End Date", disabled=True),
            "Status": st.column_config.SelectboxColumn("Status", options=["Not Started", "In Progress", "Completed"]),
            "Hours": st.column_config.NumberColumn("Hours", format="%.1f")
        }
    )

if st.button("🗑️ Reset All"):
    st.session_state.master_plan = None
    st.session_state.project_dates = {"Start": None, "End": None}
    st.rerun()
