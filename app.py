import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Jarvis Gantt Architect", layout="wide")

# --- 1. Persistent Memory ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None

# --- 2. Advanced Date & Allocation Logic ---
def add_business_days(start_date, days):
    """Calculates end date by skipping weekends."""
    current_date = start_date
    added_days = 0
    while added_days < days - 1:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5: 
            added_days += 1
    return current_date

def run_sequential_allocation(dev_names, qa_names, lead_names, data, num_sprints, start_date, sprint_days):
    generated_plan = []
    
    for i in range(num_sprints):
        # Calculate Sprint Start/End skipping weekends
        s_start = start_date + timedelta(days=i * sprint_days)
        while s_start.weekday() >= 5:
            s_start += timedelta(days=1)
            
        s_end = add_business_days(s_start, sprint_days)
        s_label = f"Sprint {i}"

        def assign_balanced(sprint, s_dt, e_dt, names, task, role, total_hrs):
            split_hrs = float(total_hrs) / len(names)
            for name in names:
                generated_plan.append({
                    "Sprint": sprint, 
                    "Start": s_dt,
                    "Finish": e_dt, 
                    "Status": "Not Started",
                    "Task": task, 
                    "Owner": name, 
                    "Role": role, 
                    "Hours": round(split_hrs, 1)
                })

        # --- DYNAMIC FLOW ALLOCATION ---
        if i == 0:
            assign_balanced(s_label, s_start, s_end, lead_names, "Analysis Phase", "Lead", data["Analysis"])
            assign_balanced(s_label, s_start, s_end, qa_names, "TC Preparation", "QA", data["TC_Prep"])
        
        elif 0 < i < (num_sprints - 1) or (num_sprints == 2 and i == 1):
            exec_count = max(1, num_sprints - 2) if num_sprints > 2 else 1
            assign_balanced(s_label, s_start, s_end, dev_names, "Development Phase", "Dev", data["Dev"]/exec_count)
            assign_balanced(s_label, s_start, s_end, lead_names, "Code Review (Initial)", "Lead", data["Review"]/exec_count)
            assign_balanced(s_label, s_start, s_end, qa_names, "QA Testing", "QA", data["QA_Test"]/exec_count)
            assign_balanced(s_label, s_start, s_end, dev_names, "Bug Fixes (Initial)", "Dev", (data["Fixes"] * 0.7)/exec_count)

        if i == (num_sprints - 1) and i > 0:
            assign_balanced(s_label, s_start, s_end, qa_names, "Integration Testing", "QA", data["Integ"])
            assign_balanced(s_label, s_start, s_end, dev_names, "Bug Fixes (Integration)", "Dev", data["Fixes"] * 0.3)
            assign_balanced(s_label, s_start, s_end, qa_names, "Bug Retest", "QA", data["Retest"])
            assign_balanced(s_label, s_start, s_end, ["DevOps"], "Merge and Deploy", "Ops", data["Deploy"])
            assign_balanced(s_label, s_start, s_end, qa_names, "Smoke Test", "QA", data["Smoke"])

    return pd.DataFrame(generated_plan)

# --- 3. Sidebar ---
with st.sidebar:
    st.header("👥 Team Setup")
    d_names = [st.text_input(f"Dev {j+1}", f"Dev_{j+1}", key=f"d_{j}") for j in range(st.number_input("Devs", 1, 10, 3))]
    q_names = [st.text_input(f"QA {j+1}", f"QA_{j+1}", key=f"q_{j}") for j in range(st.number_input("QA", 1, 10, 1))]
    l_names = [st.text_input(f"Lead {j+1}", f"Lead_{j+1}", key=f"l_{j}") for j in range(st.number_input("Lead", 1, 10, 1))]
    
    st.divider()
    st.header("📅 Timeline Settings")
    start_date = st.date_input("Project Start", datetime(2026, 2, 9))
    num_sprints = st.number_input("Total Sprints", 2, 20, 3)
    sprint_days = st.number_input("Working Days/Sprint", 1, 60, 10)

# --- 4. Main UI ---
st.title("Jarvis Phase-Gate Manager")

with st.expander("📥 Effort Baseline", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        analysis = st.number_input("Analysis", value=25.0); dev_h = st.number_input("Dev", value=150.0)
        review = st.number_input("Review", value=20.0); fixes = st.number_input("Fixes", value=30.0)
    with c2:
        qa_h = st.number_input("QA", value=80.0); tc_p = st.number_input("TC Prep", value=40.0)
        retest = st.number_input("Retest", value=15.0); integ = st.number_input("Integration", value=20.0)
        smoke = st.number_input("Smoke", value=8.0); deploy = st.number_input("Deploy", value=6.0)

if st.button("🚀 SYNC & GENERATE TIMELINE", type="primary", use_container_width=True):
    inputs = {"Analysis": analysis, "Dev": dev_h, "Fixes": fixes, "Review": review, "QA_Test": qa_h, 
              "TC_Prep": tc_p, "Retest": retest, "Integ": integ, "Smoke": smoke, "Deploy": deploy}
    st.session_state.master_plan = run_sequential_allocation(d_names, q_names, l_names, inputs, num_sprints, start_date, sprint_days)
    st.rerun()

# --- 5. Visualized Output ---
if st.session_state.master_plan is not None:
    st.subheader("📅 Project Gantt Chart")
    gantt_fig = px.timeline(st.session_state.master_plan, x_start="Start", x_end="Finish", y="Task", color="Role", 
                            hover_data=["Owner", "Hours"], category_orders={"Task": st.session_state.master_plan["Task"].unique()})
    gantt_fig.update_yaxes(autorange="reversed")
    st.plotly_chart(gantt_fig, use_container_width=True)

    st.subheader("📝 Roadmap Detail")
    st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)

if st.button("🗑️ Reset"):
    st.session_state.master_plan = None
    st.rerun()
