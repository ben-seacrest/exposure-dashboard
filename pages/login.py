import streamlit as st

def login_page():
    with st.container(border=False):
        col1, col2, col3 = st.columns([1,3,1], vertical_alignment="top")
        
        with col2:
            st.markdown("")

            with st.container(border=False):

                st.markdown(
                    """
                    <div style="text-align: center; font-size: 1rem; color: "#3c3c3c";>
                        Log in to your account
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                email_input = st.text_input("Email")
                password_input = st.text_input("Password", type="password")

                login_button = st.button(key="login_button", label="Log In", use_container_width=True, type='secondary', icon=":material/login:")
                
                if login_button:
                    user_id, email, first_name, last_name = authorise_user(email_input, password_input)
                    if email:
                        # Reset the logged_out state when logging in successfully
                        st.session_state["logged_out"] = False
                        st.session_state["logged_in"] = True
                        st.session_state["user_id"] = user_id
                        st.session_state["first_name"] = first_name
                        st.session_state["last_name"] = last_name
                        st.session_state["email"] = email

                        st.info(f"Logged in successfully!")
                        st.session_state["current_page"] = "Dashboard"
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Incorrect email or password. Please try again.")  

            st.markdown(
                """
                <div style="display: flex; align-items: center; text-align: center; margin: 5px 0px 15px 0px;">
                    <hr style="flex-grow: 1; border: none; border-top: 1px solid #E8E8E8;" />
                    <span style="margin: 0 30px; color: #E8E8E8; font-size: 1rem;">or</span>
                    <hr style="flex-grow: 1; border: none; border-top: 1px solid #E8E8E8;" />
                </div>
                """,
                unsafe_allow_html=True
            )
    
if __name__ == "__main__":
    login_page()
