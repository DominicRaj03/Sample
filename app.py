import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Jarvis Persistent Editor", layout="wide")

# --- 1. Initialize Memory (Session State) ---
# This acts as the "database" for the current session
if 'roadmap_data' not in st.session_state:
    st.session_state.roadmap_data = None  # Holds the DataFrame
if 'generation_trigger' not in st.session_state:
    st.session_state.generation_trigger = False

# --- 2. Allocation Logic ---
def generate_initial_roadmap(dev_names, qa_names, lead_names, inputs, num_sprints):
    data = []
    sprint_list = [f"Sprint {i}" for i in range(num_sprints)]
    
    # Simple Sequential Logic for the initial "Draft"
    # Sprint 0
    data.append({"Sprint": "Sprint 0", "Task": "Analysis & Setup", "Owner": lead_names[0], "Hours": float(inputs["Analysis"])})
    
    # Middle Sprints (Dev & QA)
    dev_share = inputs["Dev"] / max(1, (num_sprints - 2))
    for i in range(1, num_sprints - 1):
        data.append({"Sprint": f"Sprint {i}", "Task": "Development", "Owner": dev_names[0], "Hours": float(dev_share)})
    
    # Last Sprint
    data.append({"Sprint": sprint_list[-1], "Task": "Deployment & Smoke", "Owner": "DevOps", "Hours": float(inputs["Deploy"])})
    
    return pd.DataFrame(data)

# --- 3. Sidebar Inputs ---
with st.sidebar:
    st.header("👥 Team")
    dev_names = [st.text_input("Dev Name", "D1")]
    qa_names = [st.text_input("QA Name", "Q1")]
    lead_names = [st.text_input("Lead Name", "L1")]
    num_sprints = st.number_input("Sprints", 2, 10, 4)
    
    st.divider()
    # This button triggers the initial creation ONLY
    if st.button("🚀 GENERATE INITIAL PLAN", type="primary"):
        st.session_state.generation_trigger = True

# --- 4. Main Dashboard ---
st.title("Jarvis Phase-Gate Manager")

# Effort Inputs
with st.expander("📥 Effort Baseline"):
    inputs = {
        "Analysis": st.number_input("Analysis", value=20.0),
        "Dev": st.number_input("Development", value=100.0),
        "Deploy": st.number_input("Deployment", value=10.0)
    }

# Logic to handle the "Generate" event
if st.session_state.generation_trigger:
    st.session_state.roadmap_data = generate_initial_roadmap(dev_names, qa_names, lead_names, inputs, num_sprints)
    st.session_state.generation_trigger = False # Reset trigger so it doesn't overwrite on next edit

# --- 5. The Persistent Editor ---
if st.session_state.roadmap_data is not None:
    st.info("💡 Changes to 'Hours' below are now saved automatically.")
    
    # We display and UPDATE the session state directly
    # Using 'key' ensures the widget stays linked to the data
    updated_df = st.data_editor(
        st.session_state.roadmap_data,
        use_container_width=True,
        key="main_editor",
        num_rows="dynamic" # Allows you to add/delete rows too
    )
    
    # Save back to state
    st.session_state.roadmap_data = updated_df

    # --- Summary Widget ---
    st.divider()
    total_h = st.session_state.roadmap_data["Hours"].sum()
    st.metric("Live Project Total", f"{total_h:.1f} hrs")
else:
    st.write("Please configure the team and click **Generate** in the sidebar to start.")
