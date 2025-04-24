from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from app.config import OPENAI_API_KEY

llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo", openai_api_key=OPENAI_API_KEY)

# Template to classify email
classification_prompt = PromptTemplate.from_template("""
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
Body: {body}
---

Respond with only the classification: IMMEDIATE_RESPONSE, RESPONSE_NEEDED, NO_RESPONSE.
""")

def classify_email(sender, subject, body):
    prompt = classification_prompt.format(sender=sender, subject=subject, body=body)
    response = llm([HumanMessage(content=prompt)])
    return response.content.strip().upper()

# Template to generate reply to an email
reply_prompt = PromptTemplate.from_template("""
You are an assistant helping a user write polite and concise replies to emails.

Given the email details, draft a reply that the user can review and send.

From: {sender}
Subject: {subject}
Body: {body}
                                            
Don't include subject in the reply email
                                            
Sign off with:
{signature}                                       

Reply as if you are the user, and keep it professional yet friendly.
""")
def generate_reply(sender, subject, body,signature):
    prompt = reply_prompt.format(sender=sender, subject=subject, body=body,signature=signature)
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()