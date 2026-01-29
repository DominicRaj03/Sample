import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Jarvis Executive Intelligence", layout="wide")

# --- 1. Persistent Memory ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'quality_data' not in st.session_state:
    st.session_state.quality_data = pd.DataFrame()

# --- 2. Allocation Logic ---
def run_allocation(devs, qas, leads, planning_data, num_sprints, start_date, sprint_days):
    plan = []
    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days - 1)
        s_label = f"Sprint {i}"

        def assign(task, role, names, total_hrs):
            if total_hrs <= 0: return
            split = float(total_hrs) / len(names)
            for name in names:
                plan.append({
                    "Sprint": s_label, 
                    "Start": s_start, 
                    "Finish": s_end, 
                    "Task": task, 
                    "Owner": name, 
                    "Role": role, 
                    "Hours": round(split, 1)
                })

        if i == 0:
            assign("Analysis Phase", "Lead", leads, planning_data["Analysis"])
            assign("TC preparation", "QA", qas, planning_data["TC_Prep"])
        elif 0 < i < (num_sprints - 1):
            mid = max(1, num_sprints - 2)
            assign("Development Phase", "Dev", devs, planning_data["Dev"]/mid)
            assign("Code Review", "Lead", leads, planning_data["Review"]/mid)
            assign("QA testing", "QA", qas, planning_data["QA_Test"]/mid)
            assign("Bug retest", "QA", qas, planning_data["Retest"]/mid)
            assign("Bug Fixes", "Dev", devs, planning_data["Fixes"]/mid)
        elif i == (num_sprints - 1):
            assign("Integration Testing", "QA", qas, planning_data["Integ"])
            assign("Smoke test", "QA", qas, planning_data["Smoke"])
            assign("Merge and Deploy", "Ops", ["DevOps"], planning_data["Deploy"])
    return pd.DataFrame(plan)

# --- 3. UI Structure ---
st.title("Jarvis Phase-Gate Intelligence")

with st.expander("👥 Team Setup & Capacity Settings", expanded=st.session_state.master_plan is None):
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        d_size = st.number_input("Dev Team Size", 1, 10, 3)
        dev_list = [st.text_input(f"Dev {j+1}", f"Dev_{j+1}", key=f"d{j}") for j in range(d_size)]
    with col_t2:
        q_size = st.number_input("QA Team Size", 1, 5, 1)
        qa_list = [st.text_input(f"QA {j+1}", f"QA_{j+1}", key=f"q{j}") for j in range(q_size)]
    with col_t3:
        l_size = st.number_input("Lead Team Size", 1, 5, 1)
        lead_list = [st.text_input(f"Lead {j+1}", f"Lead_{j+1}", key=f"l{j}") for j in range(l_size)]
    
    st.divider()
    sc1, sc2, sc3 = st.columns(3)
    start_dt = sc1.date_input("Project Start", datetime(2026, 2, 9))
    num_sp = sc2.number_input("Total Sprints", 2, 12, 4)
    sp_days = sc3.number_input("Working Days/Sprint", 1, 30, 8)
    daily_limit = st.slider("Max Daily Hours", 4, 12, 8)
    capacity = sp_days * daily_limit

with st.expander("📝 Sprint Planning", expanded=True):
    pc1, pc2 = st.columns(2)
    with pc1:
        h_analysis = st.number_input("Analysis Phase", value=25.0)
        h_dev = st.number_input("Development Phase", value=350.0)
        h_fixes = st.number_input("Bug Fixes", value=40.0)
        h_review = st.number_input("Code Review", value=20.0)
        h_qa = st.number_input("QA testing", value=80.0)
    with pc2:
        h_tc = st.number_input("TC preparation", value=20.0)
        h_retest = st.number_input("Bug retest", value=15.0)
        h_integ = st.number_input("Integration Testing", value=30.0)
        h_smoke = st.number_input("Smoke test", value=10.0)
        h_deploy = st.number_input("Merge and Deploy", value=8.0)
    
    plan_inputs = {
        "Analysis": h_analysis, "Dev": h_dev, "Fixes": h_fixes, "Review": h_review,
        "QA_Test": h_qa, "TC_Prep": h_tc, "Retest": h_retest, "Integ": h_integ,
        "Smoke": h_smoke, "Deploy": h_deploy
    }

    if st.button("🚀 GENERATE DATA", use_container_width=True):
        st.session_state.master_plan = run_allocation(dev_list, qa_list, lead_list, plan_inputs, num_sp, start_dt, sp_days)
        st.session_state.quality_data = pd.DataFrame([{"Sprint": f"Sprint {i}", "Bugs Found": 0, "Test Cases": 20} for i in range(num_sp)])
        st.rerun()

tab1, tab2, tab3 = st.tabs(["🗺️ Roadmap Editor", "📊 Analytics", "🎯 Quality & Forecast"])

with tab1:
    if st.session_state.master_plan is not None:
        usage = st.session_state.master_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
        over = usage[usage['Hours'] > capacity]
        for _, row in over.iterrows():
            st.warning(f"⚠️ Capacity Alert: {row['Owner']} has {row['Hours']}h in {row['Sprint']} (Limit: {capacity}h)")
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)

with tab2: # Day-to-Day Timeline (Gantt)
    if st.session_state.master_plan is not None:
        st.subheader("Day-to-Day Timeline")
        fig_gantt = px.timeline(
            st.session_state.master_plan, 
            start="Start", 
            finish="Finish", 
            x_start="Start", 
            x_end="Finish", 
            y="Task", 
            color="Role",
            hover_data=["Owner", "Hours", "Sprint"]
        )
        fig_gantt.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_gantt, use_container_width=True)

        st.divider()
        st.subheader("Sprint Comparison Matrix")
        comparison = st.session_state.master_plan.pivot_table(index="Owner", columns="Sprint", values="Hours", aggfunc="sum").fillna(0)
        st.dataframe(comparison.style.highlight_max(axis=1, color="#501010"), use_container_width=True)

with tab3: # Quality Metrics
    if not st.session_state.quality_data.empty:
        st.subheader("Quality Metrics Chart")
        fig_quality = px.line(
            st.session_state.quality_data, 
            x="Sprint", 
            y=["Test Cases", "Bugs Found"], 
            markers=True,
            title="Stability Trend"
        )
        st.plotly_chart(fig_quality, use_container_width=True)
        
        st.subheader("Metric Input Table")
        st.session_state.quality_data = st.data_editor(st.session_state.quality_data, use_container_width=True)
