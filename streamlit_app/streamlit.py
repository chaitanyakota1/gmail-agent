import streamlit as st
import requests

st.set_page_config(page_title="Gmail Assistant", layout="wide")
st.title("📬 Gmail Assistant")

#  FastAPI backend
BASE_URL = "http://localhost:8000"

# Session state
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
if "emails" not in st.session_state:
    st.session_state.emails = []

# Enter Email
user_id = st.text_input("Enter your Gmail address:", st.session_state.user_id)

if user_id:
    st.session_state.user_id = user_id

    # Fetch emails
    if st.button("Fetch and Classify Emails"):
        try:
            resp = requests.get(f"{BASE_URL}/emails/classify/{user_id}")
            print(user_id)

            response_json = resp.json()
            if resp.status_code == 200 and "classified_emails" in resp.json():
                st.session_state.emails = resp.json()["classified_emails"]
                st.success("Emails fetched and classified successfully.")
            else:
                st.warning("You might need to log in with Gmail first.")
                login_url = f"{BASE_URL}/auth/login"
                st.markdown(f"[Click here to log in with Gmail]({login_url})")
        except Exception as e:
            st.error(f"Error: {e}")

# Display emails
for i, email in enumerate(st.session_state.emails):
    with st.expander(f"✉️ {email['subject']} ({email['classification']})", expanded=True):
        st.markdown(f"**From:** {email['from']}")
        st.markdown(f"**body:** {email['body']}")
        reply_key = f"reply_{i}"
        edited_reply = st.text_area("Edit your reply:", value=email.get("suggested_reply", ""), key=reply_key)

        if st.button(f"Send Reply to {email['from']}", key=f"send_{i}"):
            payload = {
                "recipient": email['from'],
                "subject": email['subject'],
                "reply_body": st.session_state[reply_key],
                "thread_id": email['threadId']
            }
            try:
                send_resp = requests.post(f"{BASE_URL}/emails/send/{user_id}", json=payload)
                if send_resp.status_code == 200:
                    st.success("Reply sent successfully!")
                else:
                    st.error(f"Failed to send reply: {send_resp.json().get('error')}")
            except Exception as e:
                st.error(f"Error: {e}")
