import time
import streamlit as st

def authorise_user(email_input: str, password_input: str):
    """
    Validates user credentials against st.secrets values.
    Returns tuple (email, first_name, last_name) if correct, otherwise (None, None, None).
    """
    correct_email = st.secrets["email"]
    correct_password = st.secrets["password"]

    if email_input.strip().lower() == correct_email.strip().lower() and password_input == correct_password:
        return (
            st.secrets["email"],
            st.secrets.get("first_name", ""),
            st.secrets.get("last_name", ""),
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
                    # Store session state
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
