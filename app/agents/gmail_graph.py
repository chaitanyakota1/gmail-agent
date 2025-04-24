#%%
from langgraph.graph import StateGraph, END
from langchain.schema import SystemMessage
from app.llm_utils import classify_email, generate_reply
from app.gmail.gmail import fetch_unread_emails, send_reply_email
from app.gmail.secret_manager import get_user_tokens
from langgraph.checkpoint.memory import InMemorySaver
from typing import TypedDict


# # Define the state carried across graph
class EmailState(dict):
    pass

class State(TypedDict):
    user_id: str
    emails: list
    current_index: int
    current_email: dict
    reply: str
    classification: str
    next: str

def fetch_emails_node(state: dict):
    user_id = state["user_id"]
    emails = fetch_unread_emails(user_id, max_results=5)
    state["emails"] = emails
    state["current_index"] = 0
    return state

def classify_node(state: dict):
    emails = state.get("emails", [])
    index = state.get("current_index", 0)

    if index >= len(emails):
        return END

    email = emails[index]
    classification = classify_email(email["from"], email["subject"], email["body"])
    print(f"📌 CLASSIFY: {classification} — {email['subject']}")
    state["classification"] = classification
    return state

def should_reply_node(state: dict):
    if state["classification"] in ["IMMEDIATE_RESPONSE", "RESPONSE_NEEDED"]:
        return "generate_reply"
    return "skip_reply"

def generate_reply_node(state: dict):
    user_id = state["user_id"]
    tokens = get_user_tokens(user_id)
    signature = tokens.get("signature", "Best regards,\n")

    email = state["emails"][state["current_index"]]
    reply = generate_reply(email["from"], email["subject"], email["body"], signature)

    state["reply"] = reply
    state["current_email"] = email

    print(f"🤖 Generated reply to: {email['from']} — {email['subject']}")
    return state  # ✅ Directly continue to send

def send_email_node(state: dict):
    print("📨 In send_email_node with state:", state)

    user_id = state["user_id"]
    email = state["emails"][state["current_index"]]
    reply = state["reply"]

    send_reply_email(
        user_id=user_id,
        to_email=email["from"],
        subject=email["subject"],
        reply_body=reply,
        thread_id=email["threadId"]
    )

    print(f"✅ Sent to: {email['from']} | Subject: {email['subject']}")

    # Track for Streamlit
    sent_record = {
        "to": email["from"],
        "subject": email["subject"],
        "reply": reply
    }

    if "sent_replies" not in state:
        state["sent_replies"] = []

    state["sent_replies"].append(sent_record)
    return state

def skip_reply_node(state: dict):
    print(f"⏭️ Skipping reply for index {state['current_index']}")
    return state

def check_next_email(state: dict):
    state["current_index"] += 1
    if state["current_index"] >= len(state["emails"]):
        return END
    state["next"] = "classify"
    return state

# --- Graph Setup ---

checkpointer = InMemorySaver()
graph = StateGraph(dict)

graph.add_node("fetch", fetch_emails_node)
graph.add_node("classify", classify_node)
graph.add_node("generate_reply", generate_reply_node)
graph.add_node("send", send_email_node)
graph.add_node("skip_reply", skip_reply_node)
graph.add_node("check_next", check_next_email)

graph.set_entry_point("fetch")

graph.add_edge("fetch", "classify")
graph.add_conditional_edges("classify", should_reply_node)
graph.add_edge("generate_reply", "send")
graph.add_edge("send", "check_next")
graph.add_edge("skip_reply", "check_next")
graph.add_conditional_edges("check_next", lambda s: s.get("next", END) if isinstance(s, dict) else END)

email_graph_executor = graph.compile(checkpointer=checkpointer)


def run_gmail_assistant(user_id: str):
    initial_state = {
        "user_id": user_id,
        "sent_replies": []
    }
    print("▶️ Starting Gmail Assistant for:", user_id)
    result = email_graph_executor.invoke(initial_state, config={"configurable": {"thread_id": user_id}})
    print("✅ Final state:", result)
    return result

# def fetch_emails_node(state: dict):
#     user_id = state["user_id"]
#     emails = fetch_unread_emails(user_id, max_results=2)
#     state["emails"] = emails
#     state["current_index"] = 0
#     return state

# def classify_node(state: dict):
#     emails = state.get("emails", [])
#     index = state.get("current_index", 0)

#     if index >= len(emails):
#         print("No email found at current index to classify.")
#         return END

#     email = emails[index]
#     classification = classify_email(email["from"], email["subject"], email["body"])
#     print(f"CLASSIFY: {classification}")
#     state["classification"] = classification
#     return state

# def should_reply_node(state: dict):
#     if state["classification"] in ["IMMEDIATE_RESPONSE", "RESPONSE_NEEDED"]:
#         return "generate_reply"
#     return "skip_reply"

# def generate_reply_node(state: dict):
#     user_id = state["user_id"]
#     tokens = get_user_tokens(user_id)
#     signature = tokens.get("signature", "Best regards,\n")

#     email = state["emails"][state["current_index"]]
#     reply = generate_reply(email["from"], email["subject"], email["body"], signature)

#     state["reply"] = reply
#     state["current_email"] = email

#     print(f"🔁 Paused for approval — user: {user_id}, subject: {email['subject']}")
#     return state  

# def send_email_node(state: dict):
#     print("📨 In send_email_node with state:", state)
#     if not state.get("reply"):
#         return "skip_reply"
    
#     user_id = state["user_id"]
#     email = state["emails"][state["current_index"]]
#     reply = state["reply"]

#     send_reply_email(
#         user_id=user_id,
#         to_email=email["from"],
#         subject=email["subject"],
#         reply_body=reply,
#         thread_id=email["threadId"]
#     )
#     print(f"✅ Sent to: {email['from']} | Subject: {email['subject']}")
#     state.pop("_node", None)
#     return state

# def skip_reply_node(state: dict):
#     return state

# def check_next_email(state: dict):
#     assert isinstance(state, dict), f"💥 State became {type(state)}"
#     state["current_index"] += 1
#     if state["current_index"] >= len(state["emails"]):
#         return END
#     state["next"] = "classify"
#     return state


# ### --- GRAPH --- ###
# checkpointer = InMemorySaver()
# graph = StateGraph(dict)

# graph.add_node("fetch", fetch_emails_node)
# graph.add_node("classify", classify_node)
# graph.add_node("generate_reply", generate_reply_node)
# graph.add_node("send", send_email_node)
# graph.add_node("skip_reply", skip_reply_node)
# graph.add_node("check_next", check_next_email)

# graph.set_entry_point("fetch")

# graph.add_edge("fetch", "classify")
# graph.add_conditional_edges("classify", should_reply_node)
# graph.add_edge("generate_reply", "send")        # resumes here after approval
# graph.add_edge("send", "check_next")
# graph.add_edge("skip_reply", "check_next")
# graph.add_conditional_edges("check_next", lambda s: s.get("next", END) if isinstance(s, dict) else END)

# # ✅ No need to manually intercept pause — handled by LangGraph

# email_graph_executor = graph.compile(checkpointer=checkpointer)

# ### --- ENTRYPOINT --- ###

# def run_gmail_assistant(user_id: str):
#     initial_state = {
#         "user_id": user_id
#     }
#     print("STATE in run_gmail_assistant:", initial_state)
#     result = email_graph_executor.invoke(initial_state,config={"configurable": {"thread_id": user_id}})
#     print("✅ Final state:", result)
#     return result

# def resume_gmail_assistant(state: dict):
#     user_id = state.get("user_id")
#     print("⏩ Resuming paused graph for:", user_id)
#     command = Command(resume=state)
#     result = email_graph_executor.invoke(command,config={"configurable": {"thread_id": user_id}})
#     print("✅ Resumed state:", result)
#     return result

# if __name__ == "__main__":
#     from langgraph.types import Command
#     paused_state = {
#         "user_id": "chaitanyakota27@gmail.com",
#         "_node": "generate_reply",
#         "emails": [
#             {
#                 "id": "abc123",
#                 "threadId": "abc123",
#                 "from": "test@example.com",
#                 "subject": "Test Subject",
#                 "body": "This is a test email"
#             }
#         ],
#         "current_index": 0,
#         "current_email": {
#             "id": "abc123",
#             "threadId": "abc123",
#             "from": "test@example.com",
#             "subject": "Test Subject",
#             "body": "This is a test email"
#         },
#         "reply": "This is a test reply",
#         "classification": "RESPONSE_NEEDED"
#     }

#     print("▶️ Testing manual resume")
#     result = email_graph_executor.invoke(
#         Command(resume=paused_state),
#         config={"configurable": {"thread_id": "chaitanyakota27@gmail.com"}}
#     )
#     print("✅ Manual resume result:", result)

# --- Nodes ---
