import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Jarvis Persistent Manager", layout="wide")

# --- Initialize Persistent Storage ---
if 'master_plan' not in st.session_state:
    st.session_state.master_plan = None
if 'caps' not in st.session_state:
    st.session_state.caps = {}

def calculate_base_plan(dev_names, qa_names, lead_names, data, base_cap, num_sprints):
    generated_plan = []
    sprint_list = [f"Sprint {i}" for i in range(num_sprints)]
    all_staff = dev_names + qa_names + lead_names + ["DevOps"]
    resource_load = {s: {name: 0 for name in all_staff} for s in sprint_list}
    
    # Simple assignment helper
    def assign(sprint, names, task, role, hrs):
        owner = min(names, key=lambda x: resource_load[sprint][x])
        resource_load[sprint][owner] += hrs
        return {"Sprint": sprint, "Task": task, "Owner": owner, "Role": role, "Hours": float(hrs)}

    # Logic: Sprint 0 (Analysis + 60% TC Prep)
    generated_plan.append(assign("Sprint 0", lead_names, "Analysis", "Lead", data["Analysis"]))
    generated_plan.append(assign("Sprint 0", qa_names, "TC Prep (60%)", "QA", data["TC_Prep"] * 0.6))

    # Logic: Sprints 1 to N-1 (Dev Start)
    for i in range(1, num_sprints - 1):
        s_name = f"Sprint {i}"
        generated_plan.append(assign(s_name, dev_names, "Development Work", "Dev", data["Dev"]/(num_sprints-2)))
        
    # Logic: Sprint 2 (Remaining 40% TC Prep)
    if num_sprints > 2:
        generated_plan.append(assign("Sprint 2", qa_names, "TC Prep (Remaining 40%)", "QA", data["TC_Prep"] * 0.4))

    # Logic: Final Sprint (Release/Stabilization)
    last_s = f"Sprint {num_sprints-1}"
    generated_plan.append(assign(last_s, dev_names, "Bug Fixes", "Dev", data["Fixes"]))
    generated_plan.append(assign(last_s, qa_names, "Smoke Test", "QA", data["Smoke"]))

    return pd.DataFrame(generated_plan)

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("👥 Team Split")
    d_val = st.number_input("Developers", 1, 10, 3)
    q_val = st.number_input("QA", 1, 10, 1)
    l_val = st.number_input("Lead", 1, 5, 1)
    
    num_sprints = st.slider("Total Sprints", 2, 10, 4)
    st.divider()
    if st.button("🚀 GENERATE NEW PLAN", type="primary", use_container_width=True):
        devs = [f"Dev_{i+1}" for i in range(d_val)]
        qas = [f"QA_{i+1}" for i in range(q_val)]
        leads = [f"Lead_{i+1}" for i in range(l_val)]
        
        # Hardcoded defaults for calculation
        efforts = {"Analysis": 20, "TC_Prep": 40, "Dev": 120, "Fixes": 20, "Smoke": 10}
        
        # Save to session state
        st.session_state.master_plan = calculate_base_plan(devs, qas, leads, efforts, 80, num_sprints)
        st.rerun()

# --- Main Dashboard ---
st.title("Jarvis Phase-Gate Manager")

if st.session_state.master_plan is not None:
    st.info("💡 **Jarvis Note:** Edits in the 'Hours' column below are now saved permanently to this session.")
    
    # The key="plan_editor" is what enables the persistent saving of edits
    edited_df = st.data_editor(
        st.session_state.master_plan,
        key="plan_editor", 
        use_container_width=True,
        column_config={
            "Hours": st.column_config.NumberColumn("Hours", format="%.1f hrs"),
            "Sprint": st.column_config.SelectboxColumn("Sprint", options=[f"Sprint {i}" for i in range(10)])
        }
    )
    
    # Update the master plan with the edited values
    st.session_state.master_plan = edited_df

    # Live Summary
    st.divider()
    total_h = st.session_state.master_plan['Hours'].sum()
    st.metric("Total Project Hours (Adjusted)", f"{total_h:.1f} hrs")

else:
    st.warning("Please click 'Generate New Plan' in the sidebar to start.")
