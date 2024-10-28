import streamlit as st

# Set page config
st.set_page_config(page_title="Multi-Step Form", layout="wide")

# Define the steps
steps = ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"]

# Sidebar for navigation
st.sidebar.title("Progress")
current_step = st.sidebar.radio("", steps, index=2)

# Main content
st.title("Multi-Step Form")

# Function to create a step container
def create_step_container(step_name, is_active=False):
    with st.expander(f"{step_name}", expanded=is_active):
        col1, col2, col3 = st.columns([3,1,1])
        with col1:
            st.subheader(step_name)
        with col2:
            st.button("📋", key=f"clipboard_{step_name}")
        with col3:
            st.button("❓", key=f"help_{step_name}")
        
        if is_active:
            st.text_input("Enter some text")
            st.selectbox("Choose an option", ["Option 1", "Option 2", "Option 3"])
            st.slider("Select a value", 0, 100, 50)
            st.button("Next")

# Display all steps
for step in steps:
    create_step_container(step, is_active=(step == current_step))