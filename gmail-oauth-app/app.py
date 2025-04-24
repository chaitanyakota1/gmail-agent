from gmail_auth import authenticate_gmail
from gmail_auth import authenticate_gmail

from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

import base64
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr


# Template to classify email
prompt_template = PromptTemplate.from_template("""
You are an email triage assistant. 
If you feel that it's an system generated email and the reply would go to a individual, then classify as RESPONSE_NEEDED.
IF the email is about a JOB opening coming from an individual and 
response also goes to an individual person, then classify as IMMEDIATE_RESPONSE. 
                                               
If {sender} email doesn't feel like a human, then evaluate 
if sending response to the system makes sense, then RESPONSE_NEEDED, if not NO_RESPONSE.                                                                                                                                 

Classify the following email into one of three categories:
1. IMMEDIATE_RESPONSE
2. RESPONSE_NEEDED
3. NO_RESPONSE

Email:
---
From: {sender}
Subject: {subject}
Body: {snippet}
---

Reply ONLY with one of: IMMEDIATE_RESPONSE, RESPONSE_NEEDED, NO_RESPONSE.
""")

# Template to generate reply to an email
reply_prompt = PromptTemplate.from_template("""
You are an assistant helping a user write polite and concise replies to emails.

Given the email details, draft a reply that the user can review and send.

From: {sender}
Subject: {subject}
Body: {snippet}
                                            
Don't include subject in the reply email
                                            
Sign off with:
Best regards,
{user_name}                                         

Reply as if you are the user, and keep it professional yet friendly.
""")


llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

def classify_email(sender, subject, snippet):
    prompt = prompt_template.format(sender=sender, subject=subject, snippet=snippet)
    response = llm([HumanMessage(content=prompt)])
    classification = response.content.strip().upper()
    return classification

def generate_reply(sender, subject, snippet,user_name):
    prompt = reply_prompt.format(sender=sender, subject=subject, snippet=snippet,user_name=user_name)
    response = llm([HumanMessage(content=prompt)])
    return response.content.strip()

def review_reply(reply):
    print("\n✍️ Suggested Reply:\n")
    print(reply)
    print("\nDo you want to:")
    print("1. Approve and Send")
    print("2. Edit the reply")
    print("3. Skip")

    choice = input("Enter 1, 2, or 3: ").strip()

    if choice == '1':
        return reply  # Approved
    elif choice == '2':
        print("\nEdit your reply below. Press Enter when done:")
        edited_reply = input("Your edited reply: ")
        return edited_reply
    else:
        return None

def send_email_reply(service, to, subject, reply_body, thread_id):
    message = MIMEText(reply_body)
    name, email = parseaddr(to)
    message['to'] = email
    message['subject'] = f"Re: {subject}"
    message['from'] = "me"

    # Convert to base64 encoded string
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Send reply in the same thread
    send_message = {
        'raw': raw_message,
        'threadId': thread_id
    }

    try:
        sent_msg = service.users().messages().send(userId='me', body=send_message).execute()
        print(f"📤 Reply sent successfully. Message ID: {sent_msg['id']}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

def get_unread_emails(service,user_name):
    response = service.users().messages().list(userId='me', labelIds=['UNREAD'], maxResults=1).execute()
    messages = response.get('messages', [])

    print(f"📨 Found {len(messages)} unread emails.")

    for msg in messages:
        msg_id = msg['id']
        msg_detail = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

        headers = msg_detail['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "(No Subject)")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "(Unknown Sender)")
        snippet = msg_detail.get('snippet', '')

        classification = classify_email(sender, subject, snippet)

        print("\n--- Email ---")
        print(f"From: {sender}")
        print(f"Subject: {subject}")
        print(f"Snippet: {snippet[:200]}...")
        print(f"🧠 Classification: {classification}")

        if classification in ['RESPONSE_NEEDED', 'IMMEDIATE_RESPONSE']:
            reply = generate_reply(sender, subject, snippet,user_name)
            final_reply = review_reply(reply)

            if final_reply:
                print("\n✅ Reply marked for sending:")
                print(final_reply)
                send_email_reply(service, sender, subject, final_reply, msg_detail['threadId'])

            else:
                print("⏭️ Skipped this reply.")

def main():
    service = authenticate_gmail()
    user_name = input("Please enter your name for the email signature (e.g., Chaitanya Kota): ").strip()
    get_unread_emails(service,user_name)

if __name__ == '__main__':
    main()