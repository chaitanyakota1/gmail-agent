import streamlit as st
import requests

BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="📨 Gmail LangGraph Assistant", layout="wide")
st.title("📨 Gmail LangGraph Assistant")

# Session state initialization
if "state" not in st.session_state:
    st.session_state.state = None
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
if "email_checked" not in st.session_state:
    st.session_state.email_checked = False

# Step 1: Gmail Login
user_id = st.text_input("Enter your Gmail address:", st.session_state.user_id)
if user_id:
    st.session_state.user_id = user_id

    if not st.session_state.email_checked:
        st.info("🔒 Checking Gmail access...")
        login_check = requests.get(f"{BASE_URL}/auth/check/{user_id}")
        if login_check.status_code == 200 and login_check.json().get("authorized"):
            st.success("✅ Gmail access confirmed.")
            st.session_state.email_checked = True
        else:
            st.warning("You need to log in with Gmail first.")
            st.markdown(f"[Click here to log in]({BASE_URL}/auth/login)")
            st.stop()

# Step 2: Start LangGraph agent
if st.button("Start Gmail Agent"):
    resp = requests.get(f"{BASE_URL}/agent/run/{st.session_state.user_id}")
    data = resp.json()

    if data.get("action") == "pause":
        st.session_state.state = data["state"]
        st.success("Reply generated. Please review and approve.")
    else:
        st.info("✅ Agent finished or no reply needed.")

# Step 3: Pause state - show review interface
if st.session_state.state and "current_email" in st.session_state.state:
    email = st.session_state.state["current_email"]
    st.markdown(f"**From:** {email['from']}")
    st.markdown(f"**Subject:** {email['subject']}")
    edited = st.text_area("Generated Reply:", value=st.session_state.state["reply"], key="edited_reply")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Approve and Send"):
            st.session_state.state["reply"] = edited
            resume_resp = requests.post(f"{BASE_URL}/agent/resume", json=st.session_state.state)
            st.session_state.state = None
            st.success("✅ Reply sent and agent resumed.")
    with col2:
        if st.button("❌ Discard"):
            st.session_state.state["reply"] = ""
            resume_resp = requests.post(f"{BASE_URL}/agent/resume", json=st.session_state.state)
            st.session_state.state = None
            st.info("❌ Reply discarded. Agent resumed.")
