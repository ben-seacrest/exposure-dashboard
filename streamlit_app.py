import streamlit as st
from pages import dashboard, login, logout

st.set_page_config(
    layout="centered",
    initial_sidebar_state="auto",
    menu_items={
        'Get Help': 'https://www.seacrestmarkets.io/',
        'Report a bug': 'https://www.seacrestmarkets.io/',
        'About': "# This is a header. This is an *extremely* cool app!"
    })

# Define pages with icons
login_page = st.Page(page=login.login_page, title="Login", icon=":material/login:")
dashboard_page = st.Page(page=dashboard.dashboard_page, title="Dashboard", icon=":material/dashboard:")
logout_page = st.Page(page=logout.logout_page, title="Logout", icon=":material/logout:")

# Group pages for logged-out users
logged_out_pages = [login_page]

# Group pages for logged-in users
logged_in_pages = {
    "Monitoring": [dashboard_page],
    "Settings": [logout_page]  # Logout page added here
}

def create_navigation(pages):
    # Create the navigation sidebar
    selected_page = st.navigation(pages, position="sidebar")
    # Run the selected page function
    selected_page.run()
    
def main():
    # Initialize session state keys with default values
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "logged_out" not in st.session_state:
        st.session_state["logged_out"] = False
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None  # Default to None or another appropriate default value
    if "first_name" not in st.session_state:
        st.session_state["first_name"] = None
    if "last_name" not in st.session_state:
        st.session_state["last_name"] = None
    if "email" not in st.session_state:
        st.session_state["email"] = None

    # Display pages based on login state
    if st.session_state["logged_in"]:
        create_navigation(logged_in_pages)
    else:
        create_navigation(logged_out_pages)

# Run the main function when the script is executed
if __name__ == "__main__":
    main()
      
