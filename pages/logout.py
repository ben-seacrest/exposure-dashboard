import streamlit as st
from streamlit_extras.switch_page_button import switch_page

# Function to create the logout dialog
@st.dialog("Logout")
def logout_dialog():
    st.write("Are you sure you want to log out?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes", type="secondary", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["logged_out"] = True
            st.success("Logged out successfully!")
            # Reset session state to prepare for next login
            st.session_state["logged_out"] = False
            st.rerun()
    with col2:
        if st.button("No", type="primary", use_container_width=True):
            switch_page("Dashboard")
            st.rerun()

def logout_page():
    # Ensure session state variables are set
    if 'logged_out' not in st.session_state:
        st.session_state.logged_out = False

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = True

    # Show the logout dialog if the user is attempting to log out
    if st.session_state.logged_in and not st.session_state.logged_out:
        logout_dialog()

if __name__ == "__main__":
    logout_page()
