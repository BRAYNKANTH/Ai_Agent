from fastapi import FastAPI, HTTPException, Request, Depends
from dotenv import load_dotenv
import os
from pathlib import Path

# Load env before importing DB modules
load_dotenv()

from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from sqlmodel import Session, select
from typing import Optional
from .agent import MailAgent, Email
from .database import create_db_and_tables, get_session
from .models import User
from .meeting_database import create_meeting_db_and_tables, get_meeting_session
from .meeting_agent import MeetingAgent
from .meeting_models import Meeting
from .models import ChatHistory

app = FastAPI(title="AI Personal Assistant API")

# Middleware
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174"], # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "secret"), https_only=False, same_site="lax")

# Database
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    create_meeting_db_and_tables()

# OAuth Setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send',
        'prompt': 'consent', # Force consent to get refresh token
        'access_type': 'offline'
    }
)

# Initialize Agent
current_dir = os.path.dirname(os.path.abspath(__file__))
prompt_path = os.path.join(current_dir, "prompt.txt")

try:
    agent = MailAgent(prompt_path=prompt_path)
except FileNotFoundError:
    print(f"Warning: Prompt file not found at {prompt_path}")
    agent = None

@app.get("/")
def read_root():
    return {"message": "AI Personal Assistant API is running"}

@app.get("/auth/login")
async def login(request: Request):
    # Just clear user data, keep session object intact to avoid middleware glitches
    request.session.pop('user', None)
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not redirect_uri:
        redirect_uri = request.url_for('auth')
    # Force offline access and consent to ensure we receive a refresh_token
    return await oauth.google.authorize_redirect(request, redirect_uri, access_type='offline', prompt='consent')

from .services import GmailService
from .models import Email as EmailModel

@app.get("/auth/callback")
async def auth(request: Request, session: Session = Depends(get_session)):
    try:
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        if not redirect_uri:
            redirect_uri = request.url_for('auth')
        
        print(f"Debug - Callback Request URL: {request.url}")
        print(f"Debug - Headers: {request.headers}") # Check for Cookie header
        print(f"Debug - Session keys: {request.session.keys()}")
        print(f"Debug - State in params: {request.query_params.get('state')}")
        
        # NOTE: Authlib handles redirect_uri automatically from the request if it matches.
        # Passing it explicitly caused "multiple values" error.
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        print(f"Auth Error: {e}") # Debug print
        print(f"Debug - Session Dump: {request.session}")
        raise HTTPException(status_code=400, detail=str(e))
        
    user_info = token.get('userinfo')
    if user_info:
        # Check if user exists
        stmt = select(User).where(User.email == user_info['email'])
        user = session.exec(stmt).first()
        
        if not user:
            # Create new user
            user = User(
                email=user_info['email'],
                name=user_info['name'],
                avatar_url=user_info.get('picture'),
                provider="google"
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
        # Store user AND TOKEN in session
        # NOTE: asking for 'offline' access gives a refresh_token only the FIRST time.
        # Ideally we store these in the DB. For MVP session is fine (but refresh token might be lost if session clears)
        # Prepare token to store
        token_data = {
            "access_token": token.get('access_token'),
            "refresh_token": token.get('refresh_token'),
            "token_type": token.get('token_type'),
            "expires_in": token.get('expires_in'),
            "scope": token.get('scope'),
            "id_token": token.get('id_token'),
            "expires_at": token.get('expires_at')
        }

        # If no refresh token in new token, check if we had one previously? 
        # Actually, for MVP it's safer to just rely on force consent or re-login.
        # But let's check if the raw token has it.
        
        request.session['user'] = {
            "id": user.id,
            "email": user.email, 
            "name": user.name, 
            "picture": user.avatar_url,
            "token": token_data 
        }
        
    return RedirectResponse(url='http://localhost:5173')

@app.get("/auth/me")
def get_current_user(request: Request):
    user = request.session.get('user')
    if user:
        # Don't return the token to the frontend
        return {k: v for k, v in user.items() if k != 'token'}
    raise HTTPException(status_code=401, detail="Not authenticated")

@app.get("/auth/logout")
def logout(request: Request):
    request.session.pop('user', None)
    return {"message": "Logged out"}


from pydantic import BaseModel
class EmailRequest(BaseModel):
    subject: str
    sender: str
    received_time: str
    body_preview: str
    body: Optional[str] = None

@app.post("/api/analyze")
def analyze_email(request: EmailRequest):
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized (prompt file missing)")
    
    email = Email(
        subject=request.subject,
        sender=request.sender,
        received_time=request.received_time,
        body_preview=request.body_preview,
        body=request.body
    )
    return agent.analyze_email(email)

@app.post("/api/sync")
def sync_emails(request: Request, session: Session = Depends(get_session)):
    user_data = request.session.get('user')
    if not user_data or not user_data.get('token'):
        raise HTTPException(status_code=401, detail="Not authenticated or no token")
    
    # Get User DB object
    user = session.get(User, user_data['id'])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    service = GmailService(session, agent)
    count = service.fetch_recent_emails(user, user_data['token'])
    
    return {"message": f"Synced {count} new emails", "count": count}

@app.get("/api/emails")
def get_emails(request: Request, session: Session = Depends(get_session)):
    user_data = request.session.get('user')
    if not user_data:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Fetch recent emails from DB
    stmt = select(EmailModel).where(EmailModel.user_id == user_data['id']).order_by(EmailModel.received_time.desc()).limit(50)
    emails = session.exec(stmt).all()
    return emails

class EmailSendRequest(BaseModel):
    to: str
    subject: str
    body: str

@app.post("/api/send-email")
def send_email_endpoint(request: Request, email_request: EmailSendRequest, session: Session = Depends(get_session)):
    user_data = request.session.get('user')
    if not user_data or not user_data.get('token'):
        raise HTTPException(status_code=401, detail="Not authenticated or no token")

    user = session.get(User, user_data['id'])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not agent: # Agent might not be needed for sending, but keeping consistency service init
         pass 

    service = GmailService(session, agent) # Agent can be passed even if unused for sending
    try:
        service.send_email(user, user_data['token'], email_request.to, email_request.subject, email_request.body)
        return {"message": "Email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[list] = []

# --- AI Agent Endpoints ---

class RewriteRequest(BaseModel):
    text: str
    style: str # formal, casual, shorten, fix_grammar

@app.post("/api/agent/rewrite")
async def rewrite_email(req: RewriteRequest):
    try:
        if not req.text:
            return {"result": ""}
        
        rewritten = agent.rewrite_email(req.text, req.style)
        return {"result": rewritten}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class QueryInboxRequest(BaseModel):
    query: str

@app.post("/api/agent/query_inbox")
async def query_inbox(req: QueryInboxRequest, session: Session = Depends(get_session)):
    try:
        from .rag_agent import InboxRAGAgent
        from .models import ChatHistory # Import here to avoid circulars if any
        import datetime
        
        rag_agent = InboxRAGAgent(session)
        answer = rag_agent.query_inbox(req.query)
        
        # Save to DB
        user_msg = ChatHistory(sender="user", text=req.query, timestamp=datetime.datetime.utcnow())
        agent_msg = ChatHistory(sender="agent", text=answer, timestamp=datetime.datetime.utcnow())
        session.add(user_msg)
        session.add(agent_msg)
        session.commit()
        
        return {"result": answer}
    except Exception as e:
         print(f"Query Error: {e}")
         raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/meeting-agent/chat")
def chat_with_meeting_agent(request: ChatRequest, session: Session = Depends(get_meeting_session)):
    meeting_agent = MeetingAgent(session)
    return meeting_agent.process_message(request.message, request.conversation_history)

@app.get("/api/meetings")
def get_all_meetings(session: Session = Depends(get_meeting_session)):
    try:
        stmt = select(Meeting).order_by(Meeting.start_time)
        meetings = session.exec(stmt).all()
        return meetings
    except Exception as e:
        print(f"ERROR FETCHING MEETINGS: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history")
def get_chat_history(session: Session = Depends(get_meeting_session)):
    stmt = select(ChatHistory).order_by(ChatHistory.timestamp)
    history = session.exec(stmt).all()
    return history

@app.delete("/api/chat/history")
def clear_chat_history(session: Session = Depends(get_meeting_session)):
    stmt = select(ChatHistory)
    history = session.exec(stmt).all()
    for h in history:
        session.delete(h)
    session.commit()
    return {"message": "Chat history cleared"}

@app.delete("/api/meetings/{meeting_id}")
def delete_meeting_endpoint(meeting_id: int, session: Session = Depends(get_meeting_session)):
    meeting = session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    session.delete(meeting)
    session.commit()
    return {"message": "Meeting deleted"}

