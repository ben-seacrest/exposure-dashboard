import streamlit as st
import pandas as pd

def dashboard_page():
    first_name = st.session_state["first_name"]

    st.subheader(f"Welcome, {first_name}", anchor=False)

if __name__ == "__main__":
    dashboard_page()
