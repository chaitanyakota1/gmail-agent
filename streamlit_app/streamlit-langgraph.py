import streamlit as st
import requests
import time

st.set_page_config(page_title="📧 Gmail Assistant (LangGraph)", layout="wide")
st.title("📧 Gmail LangGraph Assistant (Auto-Send Mode)")

BASE_URL = "http://localhost:8000"

# --- Session State Initialization ---
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
if "processed_login" not in st.session_state:
    st.session_state.processed_login = False

# OAuth Redirect
query_params = st.experimental_get_query_params()
if "user_id" in query_params and not st.session_state.processed_login:
    st.session_state.user_id = query_params["user_id"][0]
    st.session_state.processed_login = True
    st.experimental_set_query_params()

# UI Login
if not st.session_state.user_id:
    st.subheader("🔐 Please login to continue")
    email_input = st.text_input("Enter your Gmail address:")
    if st.button("Login with Gmail"):
        if email_input:
            login_url = f"{BASE_URL}/auth/login?user_id={email_input}"
            st.markdown(f'<meta http-equiv="refresh" content="0; url={login_url}">', unsafe_allow_html=True)
        else:
            st.error("Please enter your Gmail address")
    st.stop()

#Login
user_id = st.session_state.user_id
st.success(f"✅ Logged in as: {user_id}")

#Actions
run_col1, run_col2 = st.columns([1, 3])
with run_col1:
    run_agent = st.button("▶️ Check for Emails")

with run_col2:
    logout = st.button("🚪 Logout")
    if logout:
        st.session_state.clear()
        st.rerun()

# GMAIL ASSISTANT RUN
if run_agent:
    with st.spinner("Running Gmail Assistant (auto-send mode)..."):
        try:
            resp = requests.get(f"{BASE_URL}/agent/run/{user_id}")
            if resp.status_code == 200:
                data = resp.json()
                st.success("✅ Assistant finished processing!")

                sent_replies = data.get("sent_replies", [])
                if sent_replies:
                    st.subheader("📬 Sent Replies:")
                    for i, r in enumerate(sent_replies, 1):
                        st.markdown(f"### ✉️ Reply #{i}")
                        st.markdown(f"**To:** {r['to']}")
                        st.markdown(f"**Subject:** {r['subject']}")
                        st.markdown("**Reply Body:**")
                        st.code(r["reply"], language="markdown")
                        st.divider()
                        time.sleep(0.6)  # Slight delay for streaming effect
                else:
                    st.info("No emails required replies.")
            else:
                st.error(f"Server error: {resp.status_code}")
        except Exception as e:
            st.error(f"Error connecting to server: {e}")
