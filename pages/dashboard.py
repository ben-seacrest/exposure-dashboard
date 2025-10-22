import streamlit as st
import pandas as pd

def dashboard_page():
    first_name = st.session_state["first_name"]

    st.title(f"Welcome, {first_name}")

if __name__ == "__main__":
    dashboard_page()
