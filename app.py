import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io
import math

st.set_page_config(page_title="Jarvis Advanced Suite", layout="wide")

# --- 1. Persistent Memory ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'sprint_meta' not in st.session_state:
    st.session_state.sprint_meta = {}

# --- 2. Logic Engines ---
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
    sprint_details = {}
    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        while s_start.weekday() >= 5: s_start += timedelta(days=1)
        s_end = add_business_days(s_start, sprint_days)
        s_label = f"Sprint {i}"
        sprint_details[s_label] = f"{s_start.strftime('%Y-%m-%d')} to {s_end.strftime('%Y-%m-%d')}"

        def assign_balanced(sprint, s_dt, e_dt, names, task, role, total_hrs):
            split_hrs = float(total_hrs) / len(names)
            for name in names:
                generated_plan.append({
                    "Sprint": sprint, "Start": s_dt, "Finish": e_dt,
                    "Task": task, "Owner": name, "Role": role, "Hours": round(split_hrs, 1)
                })

        if i == 0:
            assign_balanced(s_label, s_start, s_end, lead_names, "Requirement/Analysis", "Lead", data["Analysis"])
            assign_balanced(s_label, s_start, s_end, qa_names, "TC Preparation", "QA", data["TC_Prep"])
        elif 0 < i < (num_sprints - 1) or (num_sprints == 2 and i == 1):
            exec_count = max(1, num_sprints - 2) if num_sprints > 2 else 1
            assign_balanced(s_label, s_start, s_end, dev_names, "Development Phase", "Dev", data["Dev"]/exec_count)
            assign_balanced(s_label, s_start, s_end, lead_names, "Code Review", "Lead", data["Review"]/exec_count)
            assign_balanced(s_label, s_start, s_end, qa_names, "QA Testing & Bug Retest", "QA", (data["QA_Test"] + data["Retest"])/exec_count)
        if i == (num_sprints - 1) and i > 0:
            assign_balanced(s_label, s_start, s_end, qa_names, "Integration Testing", "QA", data["Integ"])
            assign_balanced(s_label, s_start, s_end, dev_names, "Final Bug Fixes", "Dev", data["Fixes"])
            assign_balanced(s_label, s_start, s_end, ["DevOps"], "Merge & Deploy", "Ops", data["Deploy"])
            assign_balanced(s_label, s_start, s_end, qa_names, "Smoke Testing", "QA", data["Smoke"])
            
    return pd.DataFrame(generated_plan), sprint_details

# --- 3. Sidebar ---
with st.sidebar:
    st.header("👥 Team Setup")
    d_count = st.number_input("Devs", 1, 10, 3); q_count = st.number_input("QA", 1, 10, 1); l_count = st.number_input("Lead", 1, 10, 1)
    dev_names = [st.text_input(f"Dev {j+1}", f"Dev_{j+1}", key=f"d_{j}") for j in range(d_count)]
    qa_names = [st.text_input(f"QA {j+1}", f"QA_{j+1}", key=f"q_{j}") for j in range(q_count)]
    lead_names = [st.text_input(f"Lead {j+1}", f"Lead_{j+1}", key=f"l_{j}") for j in range(l_count)]
    
    st.divider(); st.header("📅 Settings")
    start_date_in = st.date_input("Project Start", datetime(2026, 2, 9))
    num_sprints_in = st.number_input("Total Sprints", 2, 20, 3)
    sprint_days_in = st.number_input("Working Days/Sprint", 1, 60, 8)
    daily_hrs_in = st.slider("Max Daily Hrs/Person", 4, 12, 8)
    sidebar_sync = st.button("🔄 Sync & Calculate", type="primary", use_container_width=True)

# --- 4. Main UI ---
st.title("Jarvis Phase-Gate Intelligence")
tab1, tab2, tab3 = st.tabs(["🗺️ Roadmap Editor", "📈 Analytics & Process Gantt", "🔍 Sprint Inspector"])

capacity = sprint_days_in * daily_hrs_in

with tab1:
    with st.expander("📥 Effort Baseline", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            analysis = st.number_input("Analysis", value=25.0); dev_h = st.number_input("Dev", value=150.0)
            review = st.number_input("Review", value=18.0); fixes = st.number_input("Fixes", value=20.0)
        with c2:
            qa_h = st.number_input("QA", value=85.0); tc_p = st.number_input("TC Prep", value=20.0)
            retest = st.number_input("Retest", value=10.0); integ = st.number_input("Integration", value=20.0)
            smoke = st.number_input("Smoke", value=5.0); deploy = st.number_input("Deploy", value=6.0)

    if st.button("🚀 GENERATE DATA", use_container_width=True) or sidebar_sync:
        inputs = {"Analysis": analysis, "Dev": dev_h, "Fixes": fixes, "Review": review, "QA_Test": qa_h, 
                  "TC_Prep": tc_p, "Retest": retest, "Integ": integ, "Smoke": smoke, "Deploy": deploy}
        df, meta = run_sequential_allocation(dev_names, qa_names, lead_names, inputs, num_sprints_in, start_date_in, sprint_days_in)
        st.session_state.master_plan = df
        st.session_state.sprint_meta = meta
        st.rerun()

    if st.session_state.master_plan is not None:
        # --- VALIDATION WARNINGS ---
        check_pivot = st.session_state.master_plan.groupby(["Owner", "Sprint"])["Hours"].sum().reset_index()
        overloaded = check_pivot[check_pivot["Hours"] > capacity]
        if not overloaded.empty:
            for _, row in overloaded.iterrows():
                st.error(f"⚠️ **Validation Warning:** {row['Owner']} is over-allocated in {row['Sprint']} ({row['Hours']}h > {capacity}h capacity).")

        st.subheader("Sprint Comparison")
        st.plotly_chart(px.bar(st.session_state.master_plan, x="Sprint", y="Hours", color="Role", barmode="group", height=300), use_container_width=True)
        
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)
        
        excel_data = io.BytesIO()
        st.session_state.master_plan.to_excel(excel_data, index=False)
        st.download_button("📥 Download Roadmap (Excel)", excel_data.getvalue(), "Roadmap.xlsx")

with tab2:
    if st.session_state.master_plan is not None:
        st.subheader("🗓️ Project Process Milestones")
        milestone_df = st.session_state.master_plan.groupby("Task").agg({"Start": "min", "Finish": "max"}).reset_index()
        st.plotly_chart(px.timeline(milestone_df, x_start="Start", x_end="Finish", y="Task", color="Task"), use_container_width=True)

        st.subheader("📊 Workload Analytics")
        resource_pivot = st.session_state.master_plan.pivot_table(index="Owner", columns="Sprint", values="Hours", aggfunc="sum", fill_value=0)
        st.dataframe(resource_pivot.style.applymap(lambda x: 'color: red' if x > capacity else ''), use_container_width=True)

with tab3:
    if st.session_state.master_plan is not None:
        sprint_options = ["All Sprints"] + sorted(list(st.session_state.sprint_meta.keys()))
        selected_sprint = st.selectbox("Select Sprint to Inspect", sprint_options)
        
        filtered_df = st.session_state.master_plan if selected_sprint == "All Sprints" else st.session_state.master_plan[st.session_state.master_plan["Sprint"] == selected_sprint]
        
        st.subheader(f"Resource Task Split: {selected_sprint}")
        st.dataframe(filtered_df[["Owner", "Task", "Hours", "Role"]].sort_values("Owner"), use_container_width=True)
        
        st.plotly_chart(px.sunburst(filtered_df, path=["Owner", "Task"], values="Hours", color="Owner"), use_container_width=True)
