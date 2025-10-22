import time
import streamlit as st


def get_all_users():
    """Return dict of all users defined in Streamlit secrets."""
    if "users" not in st.secrets:
        return {}
    return st.secrets["users"]


def authorise_user(email_input: str, password_input: str):
    """
    Validate login credentials against users stored in st.secrets.
    Returns (email, first_name, last_name) on success, else (None, None, None).
    """
    users = get_all_users()
    for _, user in users.items():
        if (
            email_input.strip().lower() == user.get("email", "").strip().lower()
            and password_input == user.get("password", "")
        ):
            return (
                user.get("email"),
                user.get("first_name", ""),
                user.get("last_name", ""),
            )
    return (None, None, None)


def login_page():
    with st.container(border=False):
        col1, col2, col3 = st.columns([1, 3, 1], vertical_alignment="top")

        with col2:
            st.markdown(
                """
                <div style="text-align:center; font-size:1rem; color:#3c3c3c;">
                    Log in to your account
                </div>
                """,
                unsafe_allow_html=True,
            )

            email_input = st.text_input("Email")
            password_input = st.text_input("Password", type="password")

            login_button = st.button(
                key="login_button",
                label="Log In",
                use_container_width=True,
                type="secondary",
                icon=":material/login:",
            )

            if login_button:
                email, first_name, last_name = authorise_user(email_input, password_input)
                if email:
                    # Store in session
                    st.session_state["logged_in"] = True
                    st.session_state["email"] = email
                    st.session_state["first_name"] = first_name
                    st.session_state["last_name"] = last_name
                    st.success(f"Welcome back, {first_name}!")
                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.error("Incorrect email or password. Please try again.")


if __name__ == "__main__":
    login_page()
