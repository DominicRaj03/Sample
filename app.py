import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Phase-Gate Intelligence", layout="wide")

# --- 1. Persistent Memory ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'sprint_meta' not in st.session_state:
    st.session_state.sprint_meta = {}
if 'quality_data' not in st.session_state:
    st.session_state.quality_data = pd.DataFrame()

# --- 2. Enhanced Allocation Logic ---
def add_business_days(start_date, days):
    current_date = start_date
    added_days = 0
    while added_days < days - 1:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5: added_days += 1
    return current_date

def run_allocation(dev_names, qa_names, lead_names, data, num_sprints, start_date, sprint_days):
    generated_plan = []
    sprint_details = {}
    
    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        while s_start.weekday() >= 5: s_start += timedelta(days=1)
        s_end = add_business_days(s_start, sprint_days)
        s_label = f"Sprint {i}"
        sprint_details[s_label] = f"{s_start.strftime('%Y-%m-%d')} to {s_end.strftime('%Y-%m-%d')}"

        def assign(sprint, s_dt, e_dt, names, task, role, total_hrs):
            if total_hrs <= 0: return
            split_hrs = float(total_hrs) / len(names)
            for name in names:
                generated_plan.append({"Sprint": sprint, "Start": s_dt, "Finish": e_dt, "Task": task, "Owner": name, "Role": role, "Hours": round(split_hrs, 1)})

        # Phase Mapping Logic
        if i == 0:
            assign(s_label, s_start, s_end, lead_names, "Analysis Phase", "Lead", data["Analysis"])
            assign(s_label, s_start, s_end, qa_names, "TC preparation", "QA", data["TC_Prep"])
        
        elif 0 < i < (num_sprints - 1):
            mid_count = max(1, num_sprints - 2)
            assign(s_label, s_start, s_end, dev_names, "Development Phase", "Dev", data["Dev"]/mid_count)
            assign(s_label, s_start, s_end, lead_names, "Code Review", "Lead", data["Review"]/mid_count)
            assign(s_label, s_start, s_end, qa_names, "QA testing", "QA", data["QA_Test"]/mid_count)
            assign(s_label, s_start, s_end, qa_names, "Bug retest", "QA", data["Retest"]/mid_count)
            assign(s_label, s_start, s_end, dev_names, "Bug Fixes", "Dev", data["Fixes"]/mid_count)

        if i == (num_sprints - 1) and i > 0:
            assign(s_label, s_start, s_end, qa_names, "Integration Testing", "QA", data["Integ"])
            assign(s_label, s_start, s_end, qa_names, "Smoke test", "QA", data["Smoke"])
            assign(s_label, s_start, s_end, ["DevOps"], "Merge and Deploy", "Ops", data["Deploy"])
            
    return pd.DataFrame(generated_plan), sprint_details

# --- 3. Sidebar Configuration ---
with st.sidebar:
    st.header("👥 Team")
    d_count = st.number_input("Devs", 1, 10, 3)
    q_count = st.number_input("QA", 1, 10, 1)
    l_count = st.number_input("Leads", 1, 10, 1)
    
    dev_names = [st.text_input(f"Dev {j+1}", f"Dev_{j+1}", key=f"d{j}") for j in range(d_count)]
    qa_names = [st.text_input(f"QA {j+1}", f"QA_{j+1}", key=f"q{j}") for j in range(q_count)]
    lead_names = [st.text_input(f"Lead {j+1}", f"Lead_{j+1}", key=f"l{j}") for j in range(l_count)]
    
    st.divider()
    st.header("📅 Timeline")
    start_date = st.date_input("Project Start", datetime(2026, 2, 9))
    num_sprints = st.number_input("Total Sprints", 2, 10, 3)
    sprint_days = st.number_input("Days per Sprint", 1, 30, 8)
    daily_hrs = st.slider("Max Daily Hrs", 4, 12, 8)
    sync = st.button("🔄 Sync & Refresh", type="primary", use_container_width=True)

# --- 4. Main Interface ---
st.title("Jarvis Phase-Gate Intelligence")
tabs = st.tabs(["🗺️ Roadmap", "🔍 Inspector", "🎯 Quality & Predictive", "📈 Trends"])

capacity = sprint_days * daily_hrs

with tabs[0]:
    if st.button("🚀 GENERATE PHASE-GATE DATA", use_container_width=True) or sync:
        # Integrated Inputs
        inputs = {
            "Analysis": 25.0, "TC_Prep": 20.0, "Dev": 350.0, 
            "Review": 18.0, "QA_Test": 85.0, "Retest": 10.0,
            "Fixes": 20.0, "Integ": 20.0, "Smoke": 5.0, "Deploy": 6.0
        }
        st.session_state.master_plan, st.session_state.sprint_meta = run_allocation(
            dev_names, qa_names, lead_names, inputs, num_sprints, start_date, sprint_days
        )
        st.session_state.quality_data = pd.DataFrame([{"Sprint": s, "Test Cases": 0, "Bugs Found": 0} for s in st.session_state.sprint_meta.keys()])
        st.rerun()

    if st.session_state.master_plan is not None:
        # Capacity Warnings
        chk = st.session_state.master_plan.groupby(["Owner", "Sprint"])["Hours"].sum().reset_index()
        over = chk[chk["Hours"] > capacity]
        for _, r in over.iterrows():
            st.error(f"⚠️ Capacity Alert: {r['Owner']} at {r['Hours']}h in {r['Sprint']} (Limit: {capacity}h)")
        
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)

with tabs[2]:
    if st.session_state.master_plan is not None:
        st.subheader("Manual Quality Tracking")
        st.session_state.quality_data = st.data_editor(st.session_state.quality_data, use_container_width=True)
        
        # Predictive Engine
        q_df = st.session_state.quality_data.copy()
        valid = q_df[q_df["Test Cases"] > 0]
        density = (valid["Bugs Found"] / valid["Test Cases"]).mean() if not valid.empty else 0.12
        
        q_df["Forecasted Bugs"] = q_df.apply(lambda r: round(r["Test Cases"] * density) if r["Test Cases"] > 0 and r["Bugs Found"] == 0 else None, axis=1)
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Phase-Gate Quality Forecast**")
            st.table(q_df.fillna("-"))
        with c2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=q_df["Sprint"], y=q_df["Bugs Found"], name="Actual Bugs", mode="lines+markers"))
            f_plot = q_df.dropna(subset=["Forecasted Bugs"])
            if not f_plot.empty:
                fig.add_trace(go.Scatter(x=f_plot["Sprint"], y=f_plot["Forecasted Bugs"], name="Predicted Risk", mode="markers", marker=dict(color='red', size=12, symbol='x')))
            st.plotly_chart(fig, use_container_width=True)
