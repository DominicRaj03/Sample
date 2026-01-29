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
    generated_plan = []
    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days - 1)
        s_label = f"Sprint {i}"

        def assign(task, role, names, total_hrs):
            if total_hrs <= 0: return
            split = float(total_hrs) / len(names)
            for name in names:
                generated_plan.append({
                    "Sprint": s_label, "Start": s_start, "Finish": s_end, 
                    "Task": task, "Owner": name, "Role": role, "Hours": round(split, 1)
                })

        if i == 0:
            assign("Analysis Phase", "Lead", leads, data["Analysis"])
            assign("TC Preparation", "QA", qas, data["TC_Prep"])
        elif 0 < i < (num_sprints - 1):
            mid = max(1, num_sprints - 2)
            assign("Development Phase", "Dev", devs, data["Dev"]/mid)
            assign("Code Review", "Lead", leads, data["Review"]/mid)
            assign("QA Testing & Bug Retest", "QA", qas, data["QA_Test"]/mid)
            assign("Bug Fixes (Initial)", "Dev", devs, data["Fixes"]/mid)
        elif i == (num_sprints - 1):
            assign("Integration Testing", "QA", qas, data["Integ"])
            assign("Bug Fixes (Integration)", "Dev", devs, data["Fixes_Integ"])
            assign("Merge and Deploy", "Ops", ["DevOps"], data["Deploy"])
            
    return pd.DataFrame(generated_plan)

# --- 3. UI Layout ---
st.title("Jarvis Phase-Gate Intelligence")

with st.expander("👥 Step 1: Team & Timeline Setup", expanded=st.session_state.master_plan is None):
    c1, c2, c3 = st.columns(3)
    dev_list = [st.text_input(f"Dev {j+1}", f"Dev_{j+1}", key=f"d_u_{j}") for j in range(3)]
    qa_list = [st.text_input(f"QA {j+1}", f"QA_{j+1}", key=f"q_u_{j}") for j in range(1)]
    lead_list = [st.text_input(f"Lead {j+1}", f"Lead_{j+1}", key=f"l_u_{j}") for j in range(1)]
    
    st.divider()
    sc1, sc2, sc3 = st.columns(3)
    start_dt = sc1.date_input("Start Date", datetime(2026, 2, 9))
    num_sp = sc2.number_input("Sprints", 2, 10, 4)
    sp_len = sc3.number_input("Days/Sprint", 1, 20, 8)
    capacity = sp_len * 8

tab1, tab2, tab3 = st.tabs(["🗺️ Roadmap Editor", "📊 Analytics & Export", "🎯 Quality & Forecast"])

with tab1:
    st.subheader("🛠️ Effort Baseline")
    ec1, ec2 = st.columns(2)
    with ec1:
        vals = {
            "Analysis": st.number_input("Analysis (Hrs)", 25.0),
            "Dev": st.number_input("Development (Hrs)", 350.0),
            "Fixes": st.number_input("Initial Bug Fixes (Hrs)", 20.0)
        }
    with ec2:
        vals.update({
            "Review": st.number_input("Code Review (Hrs)", 18.0),
            "QA_Test": st.number_input("QA Testing (Hrs)", 85.0),
            "TC_Prep": st.number_input("TC Prep (Hrs)", 20.0),
            "Integ": st.number_input("Integration (Hrs)", 20.0),
            "Fixes_Integ": st.number_input("Integration Bug Fixes (Hrs)", 15.0),
            "Deploy": st.number_input("Deployment (Hrs)", 6.0)
        })

    if st.button("🚀 GENERATE DATA", use_container_width=True):
        st.session_state.master_plan = run_allocation(dev_list, qa_list, lead_list, vals, num_sp, start_dt, sp_len)
        # Initialize Quality Data to prevent blank tab
        st.session_state.quality_data = pd.DataFrame([
            {"Sprint": f"Sprint {i}", "Test Cases": 0, "Bugs Found": 0} for i in range(num_sp)
        ])
        st.rerun()

    if st.session_state.master_plan is not None:
        # Granular Split View
        sel_sprint = st.selectbox("Select Sprint to Inspect", st.session_state.master_plan["Sprint"].unique())
        st.write(f"### Resource Task Split: {sel_sprint}")
        st.dataframe(st.session_state.master_plan[st.session_state.master_plan["Sprint"] == sel_sprint][["Owner", "Task", "Hours", "Role"]], use_container_width=True)
        
        # Validation Warnings
        usage = st.session_state.master_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
        over = usage[usage['Hours'] > capacity]
        for _, row in over.iterrows():
            st.warning(f"⚠️ Capacity Alert: {row['Owner']} has {row['Hours']}h in {row['Sprint']} (Limit: {capacity}h)")

with tab2:
    if st.session_state.master_plan is not None:
        st.subheader("Task Sequence per Resource")
        fig = px.timeline(st.session_state.master_plan, x_start="Start", x_end="Finish", y="Owner", color="Task")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
        
        # Sprint Comparison
        comparison = st.session_state.master_plan.pivot_table(index="Owner", columns="Sprint", values="Hours", aggfunc="sum").fillna(0)
        st.write("**Resource Workload Summary**")
        st.dataframe(comparison.style.highlight_max(axis=1), use_container_width=True)

with tab3: # Quality & Forecast
    if not st.session_state.quality_data.empty:
        st.subheader("Quality Metric Insights")
        q_df = st.data_editor(st.session_state.quality_data, use_container_width=True)
        
        # Analytics Calculation
        q_df["Productivity"] = (q_df["Test Cases"] / 20).round(2) # Example factor
        q_df["Predicted Risk"] = (q_df["Bugs Found"] * 1.5).round(1)
        st.write("**Forecasted Quality Risk Table**")
        st.table(q_df)
