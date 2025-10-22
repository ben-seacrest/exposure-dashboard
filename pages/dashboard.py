import streamlit as st
import pandas as pd

def dashboard_page():
    user_id = st.session_state["user_id"]
    first_name = st.session_state["first_name"]

if __name__ == "__main__":
    dashboard_page()
