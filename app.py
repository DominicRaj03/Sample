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

# --- 2. Calculation Engines ---
def add_business_days(start_date, days):
    current_date = start_date
    added_days = 0
    while added_days < days - 1:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5: added_days += 1
    return current_date

def run_allocation(devs, qas, leads, data, num_sprints, start_date, sprint_days):
    generated_plan = []
    for i in range(num_sprints):
        s_start = start_date + timedelta(days=i * sprint_days)
        while s_start.weekday() >= 5: s_start += timedelta(days=1)
        s_end = add_business_days(s_start, sprint_days)
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
            assign("TC preparation", "QA", qas, data["TC_Prep"])
        elif 0 < i < (num_sprints - 1):
            mid = max(1, num_sprints - 2)
            assign("Development Phase", "Dev", devs, data["Dev"]/mid)
            assign("Code Review", "Lead", leads, data["Review"]/mid)
            assign("QA testing", "QA", qas, data["QA_Test"]/mid)
            assign("Bug Fixes", "Dev", devs, data["Fixes"]/mid)
        elif i == (num_sprints - 1):
            assign("Integration Testing", "QA", qas, data["Integ"])
            assign("Merge and Deploy", "Ops", ["DevOps"], data["Deploy"])
            
    return pd.DataFrame(generated_plan)

# --- 3. Main UI Layout ---
st.title("Jarvis Phase-Gate Intelligence")

# --- Team & Timeline Setup ---
with st.expander("👥 Step 1: Team & Timeline Setup", expanded=st.session_state.master_plan is None):
    c1, c2, c3 = st.columns(3)
    with c1:
        d_count = st.number_input("Dev Count", 1, 10, 3)
        dev_list = [st.text_input(f"Dev {j+1}", f"Dev_{j+1}", key=f"d_in_{j}") for j in range(d_count)]
    with c2:
        q_count = st.number_input("QA Count", 1, 10, 1)
        qa_list = [st.text_input(f"QA {j+1}", f"QA_{j+1}", key=f"q_in_{j}") for j in range(q_count)]
    with c3:
        l_count = st.number_input("Lead Count", 1, 5, 1)
        lead_list = [st.text_input(f"Lead {j+1}", f"Lead_{j+1}", key=f"l_in_{j}") for j in range(l_count)]
    
    st.divider()
    sc1, sc2, sc3 = st.columns(3)
    start_dt = sc1.date_input("Start Date", datetime(2026, 2, 9))
    num_sp = sc2.number_input("Number of Sprints", 2, 10, 4)
    sp_len = sc3.number_input("Working Days/Sprint", 1, 20, 8)
    daily_limit = st.slider("Max Daily Hours per Person", 4, 12, 8)
    capacity = sp_len * daily_limit

tab1, tab2, tab3 = st.tabs(["🗺️ Roadmap Editor", "📊 Analytics & Export", "🎯 Quality"])

with tab1:
    st.subheader("🛠️ Effort Baseline")
    ec1, ec2 = st.columns(2)
    with ec1:
        vals = {
            "Analysis": st.number_input("Analysis (Hrs)", 0.0, 500.0, 25.0),
            "Dev": st.number_input("Development (Hrs)", 0.0, 1500.0, 350.0),
            "Fixes": st.number_input("Bug Fixes (Hrs)", 0.0, 500.0, 20.0)
        }
    with ec2:
        vals.update({
            "Review": st.number_input("Code Review (Hrs)", 0.0, 200.0, 18.0),
            "QA_Test": st.number_input("QA Testing (Hrs)", 0.0, 500.0, 85.0),
            "TC_Prep": st.number_input("TC Prep (Hrs)", 0.0, 200.0, 20.0),
            "Integ": st.number_input("Integration (Hrs)", 0.0, 200.0, 20.0),
            "Deploy": st.number_input("Deployment (Hrs)", 0.0, 100.0, 6.0)
        })

    if st.button("🚀 GENERATE DATA", use_container_width=True):
        st.session_state.master_plan = run_allocation(dev_list, qa_list, lead_list, vals, num_sp, start_dt, sp_len)
        st.rerun()

    if st.session_state.master_plan is not None:
        # Validation Warnings
        usage_check = st.session_state.master_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
        overloaded = usage_check[usage_check['Hours'] > capacity]
        for _, row in overloaded.iterrows():
            st.warning(f"⚠️ Capacity Alert: {row['Owner']} has {row['Hours']}h in {row['Sprint']} (Limit: {capacity}h)")

        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)

with tab2:
    if st.session_state.master_plan is not None:
        st.subheader("Visual Roadmap & Sprint Comparison")
        fig = px.timeline(st.session_state.master_plan, x_start="Start", x_end="Finish", y="Owner", color="Task")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
        
        comparison = st.session_state.master_plan.pivot_table(index="Owner", columns="Sprint", values="Hours", aggfunc="sum").fillna(0)
        st.dataframe(comparison, use_container_width=True)
        
        # --- EXPORT EXCEL OPTION ---
        st.divider()
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            st.session_state.master_plan.to_excel(writer, sheet_name='Roadmap', index=False)
            comparison.to_excel(writer, sheet_name='Workload_Summary')
        
        st.download_button(
            label="📥 Export to Excel",
            data=buffer.getvalue(),
            file_name=f"Jarvis_Roadmap_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.ms-excel",
            use_container_width=True
        )
