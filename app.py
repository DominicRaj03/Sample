import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io
import math

st.set_page_config(page_title="Jarvis Intelligence Suite", layout="wide")

# --- 1. Persistent Memory ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None

# --- 2. Advanced Date & Allocation Logic ---
def add_business_days(start_date, days):
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
        s_start = start_date + timedelta(days=i * sprint_days)
        while s_start.weekday() >= 5: s_start += timedelta(days=1)
        s_end = add_business_days(s_start, sprint_days)
        s_label = f"Sprint {i}"

        def assign_balanced(sprint, s_dt, e_dt, names, task, role, total_hrs):
            split_hrs = float(total_hrs) / len(names)
            for name in names:
                generated_plan.append({
                    "Sprint": sprint, "Start": s_dt, "Finish": e_dt,
                    "Task": task, "Owner": name, "Role": role, "Hours": round(split_hrs, 1)
                })

        # Sequential Flow Logic
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
    d_count = st.number_input("Devs", 1, 10, 3)
    q_count = st.number_input("QA", 1, 10, 1)
    l_count = st.number_input("Lead", 1, 10, 1)
    
    dev_names = [st.text_input(f"Dev {j+1}", f"Dev_{j+1}", key=f"d_{j}") for j in range(d_count)]
    qa_names = [st.text_input(f"QA {j+1}", f"QA_{j+1}", key=f"q_{j}") for j in range(q_count)]
    lead_names = [st.text_input(f"Lead {j+1}", f"Lead_{j+1}", key=f"l_{j}") for j in range(l_count)]
    
    st.divider()
    st.header("📅 Settings")
    start_date = st.date_input("Project Start", datetime(2026, 2, 9))
    num_sprints = st.number_input("Total Sprints", 2, 20, 3)
    sprint_days = st.number_input("Working Days/Sprint", 1, 60, 10)
    daily_hrs = st.slider("Max Daily Hrs/Person", 4, 12, 8)

# --- 4. Main UI ---
st.title("Jarvis Phase-Gate Intelligence")

tab1, tab2 = st.tabs(["🗺️ Roadmap Detail", "📈 Resource Analytics & Recommendations"])

with tab1:
    with st.expander("📥 Effort Baseline", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            analysis = st.number_input("Analysis", value=25.0); dev_h = st.number_input("Dev", value=150.0)
            review = st.number_input("Review", value=20.0); fixes = st.number_input("Fixes", value=30.0)
        with c2:
            qa_h = st.number_input("QA", value=80.0); tc_p = st.number_input("TC Prep", value=40.0)
            retest = st.number_input("Retest", value=15.0); integ = st.number_input("Integration", value=20.0)
            smoke = st.number_input("Smoke", value=8.0); deploy = st.number_input("Deploy", value=6.0)

    if st.button("🚀 SYNC & CALCULATE", type="primary", use_container_width=True):
        inputs = {"Analysis": analysis, "Dev": dev_h, "Fixes": fixes, "Review": review, "QA_Test": qa_h, 
                  "TC_Prep": tc_p, "Retest": retest, "Integ": integ, "Smoke": smoke, "Deploy": deploy}
        st.session_state.master_plan = run_sequential_allocation(dev_names, qa_names, lead_names, inputs, num_sprints, start_date, sprint_days)
        st.rerun()

    if st.session_state.master_plan is not None:
        st.data_editor(st.session_state.master_plan, use_container_width=True)

with tab2:
    if st.session_state.master_plan is not None:
        st.subheader("Hourly Split & Capacity Insight")
        capacity_per_sprint = sprint_days * daily_hrs
        
        resource_pivot = st.session_state.master_plan.pivot_table(
            index="Owner", columns="Sprint", values="Hours", aggfunc="sum", fill_value=0
        )
        
        def highlight_overload(val):
            return 'color: red; font-weight: bold' if val > capacity_per_sprint else ''
        st.dataframe(resource_pivot.style.applymap(highlight_overload))
        
        # --- RECOMMENDATION LOGIC ---
        st.divider()
        st.subheader("🤖 Jarvis Resource Recommendations")
        
        overloaded_resources = []
        for owner in resource_pivot.index:
            max_load = resource_pivot.loc[owner].max()
            if max_load > capacity_per_sprint:
                overloaded_resources.append((owner, max_load))
        
        if overloaded_resources:
            for res, load in overloaded_resources:
                excess = load - capacity_per_sprint
                role = st.session_state.master_plan[st.session_state.master_plan['Owner'] == res]['Role'].iloc[0]
                
                st.warning(f"**{res} ({role})** is overloaded by **{round(excess, 1)} hours** in peak sprints.")
                
                # Calculation for fix
                extra_days_needed = math.ceil(excess / daily_hrs)
                st.info(f"👉 **Recommendation:** To fix this, increase Sprint Days by **{extra_days_needed} days** OR add 1 more **{role}** to the team.")
        else:
            st.success("✅ **Team health is optimal.** All resources are within their defined capacity.")

if st.button("🗑️ Reset"):
    st.session_state.master_plan = None
    st.rerun()
