from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from email.utils import parsedate_to_datetime
from email.mime.text import MIMEText
import datetime
from .models import Email, User
from .agent import MailAgent, Email as AgentEmail
from sqlmodel import Session, select
import os
import time


def get_email_body(payload):
    """
    Recursively extracts the plain text or HTML body from Gmail payload.
    """
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data')
                if data:
                    body += base64.urlsafe_b64decode(data).decode()
            elif part['mimeType'] == 'text/html':
                # Prefer HTML if available (or handle both? For now keep simple text logic or append)
                # Ideally we want plain text for analysis and view, or sanitizer HTML.
                # Let's fallback to plain text if possible, or extract text from HTML.
                pass
            elif part['mimeType'] == 'multipart/alternative':
                 body += get_email_body(part)
    else:
        # No parts, just body
        data = payload['body'].get('data')
        if data:
            body = base64.urlsafe_b64decode(data).decode()
    return body

class GmailService:
    def __init__(self, session: Session, agent: MailAgent):
        self.session = session
        self.agent = agent

    def send_email(self, user: User, token: dict, to: str, subject: str, body: str):
        try:
            # Ensure we have a refresh token
            if not token.get('refresh_token'):
                print("WARNING: No refresh token found. Token expiration will fail.")

            creds = Credentials(
                token=token['access_token'],
                refresh_token=token.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                scopes=['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']
            )

            service = build('gmail', 'v1', credentials=creds)

            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            body = {'raw': raw}

            sent_message = service.users().messages().send(userId='me', body=body).execute()
            return sent_message
        except Exception as e:
            print(f"Error sending email: {e}")
            raise e

    def fetch_recent_emails(self, user: User, token: dict):
        try:
            creds = Credentials(
                token=token['access_token'],
                refresh_token=token.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                scopes=['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']
            )

            service = build('gmail', 'v1', credentials=creds)
            
            # List messages
            results = service.users().messages().list(userId='me', maxResults=10).execute()
            messages = results.get('messages', [])

            new_emails = []
            
            for msg_meta in messages:
                msg_id = msg_meta['id']
                
                # Check if already exists (naive check by subject/sender/time combo usually better, but for now ID)
                # Ideally store msg_id in DB. For MVP skipping "already exists" check complex logic.
                
                msg = service.users().messages().get(userId='me', id=msg_id).execute()
                
                payload = msg['payload']
                headers = payload.get('headers', [])
                
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
                sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
                date_str = next((h['value'] for h in headers if h['name'] == 'Date'), None)
                
                received_time = parsedate_to_datetime(date_str) if date_str else datetime.datetime.utcnow()
                
                snippet = msg.get('snippet', '')
                
                # Extract Body
                body = get_email_body(payload)
                
                # Analyze
                agent_email = AgentEmail(subject, sender, received_time.isoformat(), snippet, body)
                
                # EXTRACT GMAIL ID
                gmail_id = msg_id # 'id' field from message meta

                # DEDUPLICATION CHECK
                existing_email = self.session.exec(select(Email).where(Email.gmail_id == gmail_id)).first()
                if existing_email:
                    print(f"Skipping duplicate email: {gmail_id}")
                    continue

                # Analyze (Only if new)
                
                # Rate limit: Sleep to avoid hitting 15 RPM
                time.sleep(2) # Reduced from 4s since we skip duplicates now

                analysis = self.agent.analyze_email(agent_email)
                
                # Save to DB
                email_db = Email(
                    gmail_id=gmail_id, # Save ID
                    user_id=user.id,
                    subject=subject,
                    sender=sender,
                    snippet=snippet,
                    body=body,
                    received_time=received_time,
                    intent=analysis.get('intent', 'Unknown'),
                    summary=analysis.get('summary', snippet), 
                    urgency_score=analysis.get('urgency_score', 1),
                    risk_level=analysis.get('risk_level', 'Low'),
                    priority=analysis.get('priority', 'P4'),
                    requires_action=analysis.get('requires_action', False),
                    suggested_reply=analysis.get('suggested_reply'),
                    sentiment=analysis.get('sentiment'),
                    tone=analysis.get('tone')
                )
                self.session.add(email_db)
                try:
                    self.session.commit()
                    new_emails.append(email_db)
                    print(f"✅ Saved Email: {gmail_id}")
                except Exception as e:
                    print(f"⚠️ Failed to save email {gmail_id}: {e}")
                    self.session.rollback()
            
            return len(new_emails)

        except Exception as e:
            print(f"Error fetching Gmail: {e}")
            return 0
