import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io
import numpy as np

st.set_page_config(page_title="Jarvis Predictive Intelligence", layout="wide")

# --- 1. Persistent Memory ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'sprint_meta' not in st.session_state:
    st.session_state.sprint_meta = {}
if 'quality_data' not in st.session_state:
    st.session_state.quality_data = pd.DataFrame()

# --- 2. Logic Engines ---
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

        def assign_task(sprint, s_dt, e_dt, names, task, role, total_hrs):
            split_hrs = float(total_hrs) / len(names)
            for name in names:
                generated_plan.append({"Sprint": sprint, "Start": s_dt, "Finish": e_dt, "Task": task, "Owner": name, "Role": role, "Hours": round(split_hrs, 1)})

        if i == 0:
            assign_task(s_label, s_start, s_end, lead_names, "Analysis", "Lead", data["Analysis"])
            assign_task(s_label, s_start, s_end, qa_names, "TC Prep", "QA", data["TC_Prep"])
        elif 0 < i < (num_sprints - 1) or (num_sprints == 2 and i == 1):
            exec_count = max(1, num_sprints - 2) if num_sprints > 2 else 1
            assign_task(s_label, s_start, s_end, dev_names, "Development", "Dev", data["Dev"]/exec_count)
            assign_task(s_label, s_start, s_end, qa_names, "Testing", "QA", data["QA_Test"]/exec_count)
        if i == (num_sprints - 1) and i > 0:
            assign_task(s_label, s_start, s_end, qa_names, "Integration", "QA", data["Integ"])
            assign_task(s_label, s_start, s_end, dev_names, "Final Fixes", "Dev", data["Fixes"])
            assign_task(s_label, s_start, s_end, ["DevOps"], "Deployment", "Ops", data["Deploy"])
            
    return pd.DataFrame(generated_plan), sprint_details

# --- 3. Sidebar ---
with st.sidebar:
    st.header("👥 Team Setup")
    d_count = st.number_input("Devs", 1, 10, 3); q_count = st.number_input("QA", 1, 10, 1); l_count = st.number_input("Lead", 1, 10, 1)
    dev_names = [st.text_input(f"D{j+1}", f"Dev_{j+1}", key=f"d_{j}") for j in range(d_count)]
    qa_names = [st.text_input(f"Q{j+1}", f"QA_{j+1}", key=f"q_{j}") for j in range(q_count)]
    lead_names = [st.text_input(f"L{j+1}", f"Lead_{j+1}", key=f"l_{j}") for j in range(l_count)]
    st.divider(); st.header("📅 Settings")
    start_date = st.date_input("Start Date", datetime(2026, 2, 9))
    num_sprints = st.number_input("Total Sprints", 2, 20, 3)
    sprint_days = st.number_input("Days/Sprint", 1, 60, 8)
    daily_hrs = st.slider("Daily Max Hours", 4, 12, 8)
    sync = st.button("🔄 Sync Systems", type="primary", use_container_width=True)

# --- 4. Global Validation Logic ---
capacity = sprint_days * daily_hrs
def show_warnings():
    if st.session_state.master_plan is not None:
        chk = st.session_state.master_plan.groupby(["Owner", "Sprint"])["Hours"].sum().reset_index()
        over = chk[chk["Hours"] > capacity]
        for _, r in over.iterrows():
            st.warning(f"⚠️ **Capacity Alert:** {r['Owner']} has {r['Hours']}h in {r['Sprint']} (Max: {capacity}h)")

# --- 5. Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ Roadmap", "📊 Analytics", "🔍 Inspector", "🎯 Quality & Forecast", "📈 Trends"])

with tab1:
    show_warnings()
    if st.button("🚀 GENERATE ROADMAP", use_container_width=True) or sync:
        inputs = {"Analysis": 25, "Dev": 350, "Fixes": 20, "Review": 18, "QA_Test": 85, "TC_Prep": 20, "Integ": 20, "Deploy": 6}
        st.session_state.master_plan, st.session_state.sprint_meta = run_allocation(dev_names, qa_names, lead_names, inputs, num_sprints, start_date, sprint_days)
        st.session_state.quality_data = pd.DataFrame([{"Sprint": s, "Test Cases": 0, "Bugs Found": 0} for s in st.session_state.sprint_meta.keys()])
        st.rerun()
    if st.session_state.master_plan is not None:
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)

with tab2:
    show_warnings()
    if st.session_state.master_plan is not None:
        pivot = st.session_state.master_plan.pivot_table(index="Owner", columns="Sprint", values="Hours", aggfunc="sum", fill_value=0)
        st.dataframe(pivot.style.applymap(lambda x: 'background-color: #501010' if x > capacity else ''), use_container_width=True)

with tab4:
    show_warnings()
    if st.session_state.master_plan is not None:
        st.subheader("Manual Quality Entry")
        st.session_state.quality_data = st.data_editor(st.session_state.quality_data, use_container_width=True)
        
        # Logic: Forecast next sprint bugs based on current density
        q_df = st.session_state.quality_data.copy()
        q_df["Bug Density (%)"] = (q_df["Bugs Found"] / q_df["Test Cases"].replace(0, 1) * 100).round(2)
        
        # Simple Prediction: Moving Average Density
        avg_density = q_df[q_df["Test Cases"] > 0]["Bug Density (%)"].mean() if not q_df[q_df["Test Cases"] > 0].empty else 10.0
        q_df["Forecasted Bugs"] = q_df.apply(lambda row: round((row["Test Cases"] * avg_density / 100)) if row["Test Cases"] > 0 and row["Bugs Found"] == 0 else "-", axis=1)
        
        st.divider()
        st.subheader("🤖 Predictive Quality Forecast")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Forecasted Bug Loads per Sprint**")
            st.table(q_df[["Sprint", "Test Cases", "Bugs Found", "Forecasted Bugs"]])
        with col2:
            fig_forecast = go.Figure()
            fig_forecast.add_trace(go.Scatter(x=q_df["Sprint"], y=q_df["Bugs Found"], mode='lines+markers', name='Actual Bugs'))
            # Filter for rows where we have forecasted values (excluding '-')
            forecast_points = q_df[q_df["Forecasted Bugs"] != "-"]
            fig_forecast.add_trace(go.Scatter(x=forecast_points["Sprint"], y=forecast_points["Forecasted Bugs"], mode='markers', name='Predicted Bugs', marker=dict(color='red', dash='dash')))
            fig_forecast.update_layout(title="Bug Prediction Model")
            st.plotly_chart(fig_forecast, use_container_width=True)

        if st.button("📄 Export Executive Forecast"):
            st.markdown(f"## Quality Forecast Report - {datetime.now().strftime('%Y-%m-%d')}")
            st.write(f"Based on current data, the average bug density is **{avg_density:.2f}%**. Potential risks identified in future test cycles.")
            st.table(q_df)
            st.info("💡 Pro Tip: Use Ctrl+P to save this forecast as a PDF.")

with tab5:
    show_warnings()
    st.subheader("Cross-Project Productivity Trends")
    mock_trend = pd.DataFrame({"Project": ["P1", "P2", "P3", "Current"], "Productivity": [1.1, 1.4, 1.3, 1.7]})
    st.plotly_chart(px.line(mock_trend, x="Project", y="Productivity", title="Efficiency Gain Over Time (TC/QA Hr)"), use_container_width=True)
