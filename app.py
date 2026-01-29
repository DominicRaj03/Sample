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
def run_allocation(devs, qas, leads, data, num_sprints, start_date, sprint_days):
    plan = []
    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days - 1)
        s_label = f"Sprint {i}"

        def assign(task, role, names, total_hrs):
            if total_hrs <= 0: return
            split = float(total_hrs) / len(names)
            for name in names:
                plan.append({"Sprint": s_label, "Start": s_start, "Finish": s_end, 
                             "Task": task, "Owner": name, "Role": role, "Hours": round(split, 1)})

        if i == 0:
            assign("Analysis Phase", "Lead", leads, data["Analysis"])
            assign("TC Preparation", "QA", qas, data["TC_Prep"])
        elif 0 < i < (num_sprints - 1):
            mid = max(1, num_sprints - 2)
            assign("Development Phase", "Dev", devs, data["Dev"]/mid)
            assign("Code Review", "Lead", leads, data["Review"]/mid)
            assign("QA Testing", "QA", qas, data["QA_Test"]/mid)
        elif i == (num_sprints - 1):
            assign("Integration Testing", "QA", qas, data["Integ"])
            assign("Merge and Deploy", "Ops", ["DevOps"], data["Deploy"])
    return pd.DataFrame(plan)

# --- 3. Initial Team Input ---
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
    num_sp = sc2.number_input("Total Sprints", 2, 10, 4)
    sp_days = sc3.number_input("Working Days/Sprint", 1, 20, 8)
    daily_limit = st.slider("Max Daily Hours", 4, 12, 8)
    capacity = sp_days * daily_limit

tab1, tab2, tab3 = st.tabs(["🗺️ Roadmap Editor", "📊 Analytics & Export", "🎯 Quality Metrics"])

with tab1:
    # Effort Inputs
    vals = {"Analysis": 25.0, "Dev": 350.0, "Review": 18.0, "QA_Test": 85.0, "TC_Prep": 20.0, "Integ": 20.0, "Deploy": 6.0}
    if st.button("🚀 GENERATE DATA", use_container_width=True):
        st.session_state.master_plan = run_allocation(dev_list, qa_list, lead_list, vals, num_sp, start_dt, sp_days)
        st.session_state.quality_data = pd.DataFrame([{"Sprint": f"Sprint {i}", "Bugs Found": 0, "Test Cases": 20} for i in range(num_sp)])
        st.rerun()

    if st.session_state.master_plan is not None:
        # VALIDATION WARNINGS
        usage = st.session_state.master_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
        overloaded = usage[usage['Hours'] > capacity]
        for _, row in overloaded.iterrows():
            st.warning(f"⚠️ Capacity Alert: {row['Owner']} has {row['Hours']}h in {row['Sprint']} (Limit: {capacity}h)")

        # Resource/Sprint Split View
        sel_sprint = st.selectbox("Sprint Inspector", st.session_state.master_plan["Sprint"].unique())
        st.dataframe(st.session_state.master_plan[st.session_state.master_plan["Sprint"] == sel_sprint], use_container_width=True)
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)

with tab2: # SPRINT COMPARISON
    if st.session_state.master_plan is not None:
        st.subheader("Workload Analytics")
        comparison = st.session_state.master_plan.pivot_table(index="Owner", columns="Sprint", values="Hours", aggfunc="sum").fillna(0)
        st.dataframe(comparison.style.highlight_max(axis=1, color="#501010"), use_container_width=True)
        
        # EXPORT
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            st.session_state.master_plan.to_excel(writer, sheet_name='Roadmap', index=False)
            comparison.to_excel(writer, sheet_name='Comparison')
        st.download_button("📥 Export to Excel", buffer.getvalue(), "Jarvis_Report.xlsx", use_container_width=True)

with tab3: # QUALITY
    if not st.session_state.quality_data.empty:
        st.subheader("Sprint Quality & Risk Forecast")
        st.session_state.quality_data = st.data_editor(st.session_state.quality_data, use_container_width=True)
        # Calculate derived metrics
        q = st.session_state.quality_data
        q["Productivity"] = (q["Test Cases"] / 20).round(2)
        q["Predicted Risk"] = (q["Bugs Found"] * 1.2).round(1)
        st.table(q)
