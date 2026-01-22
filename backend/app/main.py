from fastapi import FastAPI, HTTPException, Request, Depends
from dotenv import load_dotenv
import os
from pathlib import Path

import jwt
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.security import OAuth2PasswordBearer

# Load env before importing DB modules
load_dotenv()

# Helper to strip quotes from Azure/Env vars
def get_safe_env(key, default=None):
    val = os.getenv(key, default)
    if val:
        return val.strip('"').strip("'")
    return val

# JWT Configuration
SECRET_KEY = get_safe_env("SECRET_KEY", "secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

# Auth Dependency
def get_current_user_token(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    payload = verify_token(token)
    if not payload:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload # Returns dict with user info

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

# Get allowed origins from env, default to validation set
allowed_origins_env = get_safe_env("ALLOWED_ORIGINS", "")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
# Add default local development origins
allowed_origins.extend(["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174"])
# Add production frontend URL if set
frontend_url = get_safe_env("FRONTEND_URL")
if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins, # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware, 
    secret_key=get_safe_env("SECRET_KEY", "secret"), 
    https_only=True,   # Required for SameSite="none"
    same_site="none"   # Required for cross-domain requests (frontend/backend on different domains)
)

# Database
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    create_meeting_db_and_tables()
    
    # Auto-Migration for user_email (since local script failed)
    # This is a safe, idempotent operation to ensure columns exist
    try:
        from sqlmodel import text
        with get_session() as session:
            # 1. Add user_email to meeting if missing
            try:
                session.exec(text("ALTER TABLE meeting ADD COLUMN user_email VARCHAR(255);"))
                session.commit()
                print("Migration: Added user_email to meeting table.")
            except Exception as e:
                # Ignore if column exists (MySQL error 1060: Duplicate column name)
                print(f"Migration Note (Meeting): {e}")

            # 2. Add user_email to chathistory if missing
            try:
                session.exec(text("ALTER TABLE chathistory ADD COLUMN user_email VARCHAR(255);"))
                session.commit()
                print("Migration: Added user_email to chathistory table.")
            except Exception as e:
                print(f"Migration Note (ChatHistory): {e}")
    except Exception as e:
        print(f"Migration Failed: {e}")

# OAuth Setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=get_safe_env("GOOGLE_CLIENT_ID"),
    client_secret=get_safe_env("GOOGLE_CLIENT_SECRET"),
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
    redirect_uri = get_safe_env("GOOGLE_REDIRECT_URI")
    if not redirect_uri:
        redirect_uri = str(request.url_for('auth'))
        # Azure SSL termination fix: Force HTTPS if on azurewebsites
        if "azurewebsites.net" in redirect_uri and redirect_uri.startswith("http://"):
            redirect_uri = redirect_uri.replace("http://", "https://")
            
    # Force offline access and consent to ensure we receive a refresh_token
    return await oauth.google.authorize_redirect(request, redirect_uri, access_type='offline', prompt='consent')

from .services import GmailService
from .models import Email as EmailModel

@app.get("/auth/callback")
async def auth(request: Request, session: Session = Depends(get_session)):
    try:
        redirect_uri = get_safe_env("GOOGLE_REDIRECT_URI")
        if not redirect_uri:
            redirect_uri = str(request.url_for('auth'))
            # Azure SSL termination fix: Force HTTPS if on azurewebsites
            if "azurewebsites.net" in redirect_uri and redirect_uri.startswith("http://"):
                redirect_uri = redirect_uri.replace("http://", "https://")
        
        print(f"Debug - Callback Request URL: {request.url}")
        print(f"Debug - Redirect URI used: {redirect_uri}")
        
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        print(f"Auth Error: {e}") # Debug print
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
            
        # GENERATE JWT
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "name": user.name,
            "picture": user.avatar_url,
            "google_token": token # Store Google Token inside JWT payload (or partial)
        }
        access_token = create_access_token(token_data)
    
        # Redirect to frontend with Token
        target_url = get_safe_env("FRONTEND_URL", "http://localhost:5173")
        return RedirectResponse(url=f"{target_url}?token={access_token}")

    return RedirectResponse(url=get_safe_env("FRONTEND_URL", "http://localhost:5173"))

@app.get("/auth/me")
def get_current_user(user_data: dict = Depends(get_current_user_token)):
    return user_data


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
def sync_emails(request: Request, user_data: dict = Depends(get_current_user_token), session: Session = Depends(get_session)):
    google_token = user_data.get('google_token')
    if not google_token:
        raise HTTPException(status_code=401, detail="No Google credentials in token")
    
    # Get User DB object
    user = session.exec(select(User).where(User.email == user_data['email'])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    service = GmailService(session, agent)
    count = service.fetch_recent_emails(user, google_token)
    
    return {"message": f"Synced {count} new emails", "count": count}

@app.get("/api/emails")
def get_emails(user_data: dict = Depends(get_current_user_token), session: Session = Depends(get_session)):
    email = user_data['email']
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Fetch recent emails from DB
    stmt = select(EmailModel).where(EmailModel.user_id == user.id).order_by(EmailModel.received_time.desc()).limit(50)
    emails = session.exec(stmt).all()
    return emails

class EmailSendRequest(BaseModel):
    to: str
    subject: str
    body: str

@app.post("/api/send-email")
def send_email_endpoint(email_request: EmailSendRequest, user_data: dict = Depends(get_current_user_token), session: Session = Depends(get_session)):
    google_token = user_data.get('google_token')
    if not google_token:
        raise HTTPException(status_code=401, detail="No Google credentials")

    user = session.exec(select(User).where(User.email == user_data['email'])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not agent: # Agent might not be needed for sending, but keeping consistency service init
         pass 

    service = GmailService(session, agent) # Agent can be passed even if unused for sending
    try:
        service.send_email(user, google_token, email_request.to, email_request.subject, email_request.body)
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
async def query_inbox(req: QueryInboxRequest, user_data: dict = Depends(get_current_user_token), session: Session = Depends(get_session)):
    try:
        from .rag_agent import InboxRAGAgent
        from .models import ChatHistory # Import here to avoid circulars if any
        import datetime
        
        rag_agent = InboxRAGAgent(session)
        answer = rag_agent.query_inbox(req.query)
        
        # Save to DB
        user_email = user_data.get('email')
        user_msg = ChatHistory(sender="user", text=req.query, timestamp=datetime.utcnow(), user_email=user_email)
        agent_msg = ChatHistory(sender="agent", text=answer, timestamp=datetime.utcnow(), user_email=user_email)
        session.add(user_msg)
        session.add(agent_msg)
        session.commit()
        
        return {"result": answer}
    except Exception as e:
         print(f"Query Error: {e}")
         raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/meeting-agent/chat")
def chat_with_meeting_agent(request: ChatRequest, user_data: dict = Depends(get_current_user_token), session: Session = Depends(get_meeting_session)):
    user_email = user_data['email']
    meeting_agent = MeetingAgent(session, user_email)
    return meeting_agent.process_message(request.message, request.conversation_history)

@app.get("/api/meetings")
def get_all_meetings(user_data: dict = Depends(get_current_user_token), session: Session = Depends(get_meeting_session)):
    try:
        user_email = user_data['email']
        stmt = select(Meeting).where(Meeting.user_email == user_email).order_by(Meeting.start_time)
        meetings = session.exec(stmt).all()
        return meetings
    except Exception as e:
        print(f"ERROR FETCHING MEETINGS: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history")
def get_chat_history(user_data: dict = Depends(get_current_user_token), session: Session = Depends(get_meeting_session)):
    user_email = user_data['email']
    stmt = select(ChatHistory).where(ChatHistory.user_email == user_email).order_by(ChatHistory.timestamp)
    history = session.exec(stmt).all()
    return history

@app.delete("/api/chat/history")
def clear_chat_history(user_data: dict = Depends(get_current_user_token), session: Session = Depends(get_meeting_session)):
    user_email = user_data['email']
    stmt = select(ChatHistory).where(ChatHistory.user_email == user_email)
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

