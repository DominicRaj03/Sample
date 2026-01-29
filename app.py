import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

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
            assign_task(s_label, s_start, s_end, lead_names, "Review", "Lead", data["Review"]/exec_count)
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

# --- 4. Validation Engine ---
capacity = sprint_days * daily_hrs
def show_warnings():
    if st.session_state.master_plan is not None:
        chk = st.session_state.master_plan.groupby(["Owner", "Sprint"])["Hours"].sum().reset_index()
        over = chk[chk["Hours"] > capacity]
        for _, r in over.iterrows():
            st.warning(f"⚠️ **Capacity Alert:** {r['Owner']} has {r['Hours']}h in {r['Sprint']} (Limit: {capacity}h)")

# --- 5. Main UI ---
st.title("Jarvis Phase-Gate Intelligence")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ Roadmap Editor", "📈 Analytics", "🔍 Inspector", "🎯 Quality & Forecast", "📈 Trends"])

with tab1:
    show_warnings()
    if st.button("🚀 GENERATE DATA", use_container_width=True) or sync:
        inputs = {"Analysis": 25, "Dev": 350, "Fixes": 20, "Review": 18, "QA_Test": 85, "TC_Prep": 20, "Integ": 20, "Deploy": 6}
        st.session_state.master_plan, st.session_state.sprint_meta = run_allocation(dev_names, qa_names, lead_names, inputs, num_sprints, start_date, sprint_days)
        st.session_state.quality_data = pd.DataFrame([{"Sprint": s, "Test Cases": 0, "Bugs Found": 0} for s in st.session_state.sprint_meta.keys()])
        st.rerun()
    if st.session_state.master_plan is not None:
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)

with tab4:
    show_warnings()
    if st.session_state.master_plan is not None:
        st.subheader("Quality Metrics Entry")
        st.session_state.quality_data = st.data_editor(st.session_state.quality_data, use_container_width=True)
        
        q_df = st.session_state.quality_data.copy()
        
        # Predictive Logic
        valid_entries = q_df[q_df["Test Cases"] > 0]
        avg_density = (valid_entries["Bugs Found"] / valid_entries["Test Cases"]).mean() if not valid_entries.empty else 0.10
        
        def forecast(row):
            if row["Test Cases"] > 0 and (row["Bugs Found"] == 0 or pd.isna(row["Bugs Found"])):
                return round(row["Test Cases"] * avg_density)
            return None

        q_df["Forecasted Bugs"] = q_df.apply(forecast, axis=1)
        
        st.divider()
        st.subheader("🤖 Intelligence Forecast")
        c1, c2 = st.columns(2)
        with c1:
            st.table(q_df.fillna("-"))
        with c2:
            fig = go.Figure()
            # Plot Actuals
            fig.add_trace(go.Scatter(x=q_df["Sprint"], y=q_df["Bugs Found"], mode='lines+markers', name='Actual Bugs'))
            # Plot Forecasts (filtered for numeric data)
            f_plot = q_df.dropna(subset=["Forecasted Bugs"])
            if not f_plot.empty:
                fig.add_trace(go.Scatter(x=f_plot["Sprint"], y=f_plot["Forecasted Bugs"], mode='markers', name='Predicted Risk', marker=dict(color='red', size=12, symbol='x')))
            
            fig.update_layout(title="Bug Prediction Model", xaxis_title="Sprint", yaxis_title="Bugs")
            st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.subheader("Cross-Project Productivity Trends")
    mock_trend = pd.DataFrame({"Project": ["P1", "P2", "P3", "Current"], "Productivity": [1.1, 1.4, 1.3, 1.7]})
    st.plotly_chart(px.line(mock_trend, x="Project", y="Productivity", title="Efficiency Gain Over Time (TC/QA Hr)"), use_container_width=True)
