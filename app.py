import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Jarvis Executive Intelligence", layout="wide")

# --- 1. Memory Initialization ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None

# --- 2. Logic Engine ---
def run_allocation(devs, qas, leads, planning_data, num_sprints, start_date, sprint_days):
    plan = []
    curr_dt = pd.to_datetime(start_date)
    
    for i in range(num_sprints):
        s_start = curr_dt + timedelta(days=i * sprint_days)
        s_end = s_start + timedelta(days=sprint_days - 1)
        s_label = f"Sprint {i}"

        def assign(task, role, names, total_hrs):
            if total_hrs <= 0: return
            split = float(total_hrs) / len(names)
            for name in names:
                plan.append({
                    "Sprint": s_label, "Start": s_start, "Finish": s_end, 
                    "Task": task, "Owner": name, "Role": role, "Hours": round(split, 1)
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

# --- 3. UI: Team Setup ---
st.title("Jarvis Phase-Gate Intelligence")

with st.expander("👥 Total Team Size & Capacity Settings", expanded=st.session_state.master_plan is None):
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
    num_sp = sc2.number_input("Total Sprints", 2, 24, 4)
    sp_days = sc3.number_input("Working Days/Sprint", 1, 60, 8)
    daily_limit = st.slider("Max Daily Hours/Person", 1, 24, 8)
    capacity = sp_days * daily_limit

# --- 4. Sprint Planning (Unrestricted) ---
with st.expander("📝 Sprint Planning (Effort Inputs)", expanded=True):
    pc1, pc2 = st.columns(2)
    with pc1:
        h_analysis = st.number_input("Analysis Phase", value=0.0)
        h_dev = st.number_input("Development Phase", value=0.0)
        h_fixes = st.number_input("Bug Fixes", value=0.0)
        h_review = st.number_input("Code Review", value=0.0)
        h_qa = st.number_input("QA testing", value=0.0)
    with pc2:
        h_tc = st.number_input("TC preparation", value=0.0)
        h_retest = st.number_input("Bug retest", value=0.0)
        h_integ = st.number_input("Integration Testing", value=0.0)
        h_smoke = st.number_input("Smoke test", value=0.0)
        h_deploy = st.number_input("Merge and Deploy", value=0.0)
    
    plan_inputs = {
        "Analysis": h_analysis, "Dev": h_dev, "Fixes": h_fixes, "Review": h_review,
        "QA_Test": h_qa, "TC_Prep": h_tc, "Retest": h_retest, "Integ": h_integ,
        "Smoke": h_smoke, "Deploy": h_deploy
    }

    if st.button("🚀 GENERATE ROADMAP", use_container_width=True):
        st.session_state.master_plan = run_allocation(dev_list, qa_list, lead_list, plan_inputs, num_sp, start_dt, sp_days)
        st.rerun()

# --- 5. Tabs ---
tab1, tab2 = st.tabs(["🗺️ Roadmap Editor", "📊 Analytics & Comparison"])

with tab1:
    if st.session_state.master_plan is not None:
        # Validation Warnings
        usage = st.session_state.master_plan.groupby(['Sprint', 'Owner'])['Hours'].sum().reset_index()
        over = usage[usage['Hours'] > capacity]
        
        if not over.empty:
            for _, row in over.iterrows():
                st.error(f"⚠️ Capacity Breach: {row['Owner']} assigned {row['Hours']}h in {row['Sprint']} (Limit: {capacity}h)")
        else:
            st.success(f"✅ Capacity Check: All resources are within the {capacity}h limit.")
            
        st.write("### 🛠️ Manual Roadmap Editor")
        st.session_state.master_plan = st.data_editor(st.session_state.master_plan, use_container_width=True)

with tab2:
    if st.session_state.master_plan is not None:
        # Resource Filter
        all_owners = sorted(st.session_state.master_plan["Owner"].unique().tolist())
        sel_res = st.multiselect("🔍 Filter Resources", options=all_owners, default=all_owners)
        
        # Comparison Matrix
        st.subheader("Sprint Workload Comparison")
        comp = st.session_state.master_plan.pivot_table(index="Owner", columns="Sprint", values="Hours", aggfunc="sum").fillna(0)
        st.dataframe(comp.style.background_gradient(cmap="YlOrRd"), use_container_width=True)
        
        # Gantt Timeline
        st.divider()
        st.subheader("Day-to-Day Timeline")
        df_viz = st.session_state.master_plan[st.session_state.master_plan["Owner"].isin(sel_res)].copy()
        df_viz["Start"] = pd.to_datetime(df_viz["Start"])
        df_viz["Finish"] = pd.to_datetime(df_viz["Finish"])
        
        fig = px.timeline(df_viz, x_start="Start", x_end="Finish", y="Task", color="Owner")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

        # Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            st.session_state.master_plan.to_excel(writer, sheet_name='Roadmap', index=False)
            comp.to_excel(writer, sheet_name='Workload_Comparison')
        st.download_button("📥 Export to Excel", buffer.getvalue(), "Jarvis_Roadmap.xlsx", use_container_width=True)
