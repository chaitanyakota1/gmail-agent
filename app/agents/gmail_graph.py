from langgraph.graph import StateGraph, END
from langchain.schema import SystemMessage
from app.llm_utils import classify_email, generate_reply
from app.gmail import fetch_unread_emails, send_reply_email
from app.firestore import get_user_tokens

# Define the state carried across graph
class EmailState(dict):
    pass

### Nodes ###

def fetch_emails_node(state: dict):
    user_id = state["user_id"]
    emails = fetch_unread_emails(user_id, max_results=2)
    print("🔍 Fetched emails:", emails)
    print("🔍 Type of emails:", type(emails))
    state["emails"] = emails
    state["current_index"] = 0
    return state

def classify_node(state: dict):
    email = state["emails"][state["current_index"]]
    classification = classify_email(email["from"], email["subject"], email["body"])
    print(f"CLASSIFY: {classification}")
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

    print("🔁 Pausing for approval after reply generation.")
    return {"action": "pause", "state": state} 

def send_email_node(state: dict):
    if not state.get("reply"):
        return "skip_reply"
    
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
    print(f"Sent to: {email['from']} | Subject: {email['subject']}")
    return state

def skip_reply_node(state: dict):
    return state

def check_next_email(state: dict):
    assert isinstance(state, dict), f"💥 State became {type(state)}"
    print(f"💡 Node XYZ, state type: {type(state)}, emails type: {type(state.get('emails'))}")
    print("STATE at check_next:", state)
    state["current_index"] += 1
    print(f"CHECK NEXT: current_index = {state['current_index']}, total = {len(state['emails'])}")
    if state["current_index"] >= len(state["emails"]):
        return END
    state["next"] = "classify"
    return state

### Graph Setup ###
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

email_graph_executor = graph.compile()

### Entry point ###
def run_gmail_assistant(user_id: str):
    state = {"user_id": user_id}
    print("STATE in run_gmail_assistant:", state)
    result = email_graph_executor.invoke(state)
    print("✅ Final state:", result)
    return result