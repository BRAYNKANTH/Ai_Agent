from google import genai
import json
import os
from typing import List, Dict, Any
from .models import Email
from sqlmodel import Session, select

class InboxRAGAgent:
    def __init__(self, session: Session):
        self.session = session
        # Configure Gemini Client
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)
            
        self.model_name = 'gemini-2.5-flash'
        self.embedding_model = 'models/text-embedding-004' # or appropriate model

    def query_inbox(self, user_id: int, query: str, history: List[Dict] = []) -> str:
        """
        Retrieves recent emails and answers the query using Gemini.
        """
        # Fetch last 30 emails
        stmt = select(Email).where(Email.user_id == user_id).order_by(Email.received_time.desc()).limit(30)
        emails = self.session.exec(stmt).all()
        
        if not emails:
            return "I couldn't find any recent emails in your inbox."

        # Prepare Context
        email_context = ""
        for e in emails:
            email_context += f"--- EMAIL ID {e.id} ---\nFrom: {e.sender}\nDate: {e.received_time}\nSubject: {e.subject}\nBody: {e.body or e.snippet}\n\n"

        prompt = f"""
        You are an intelligent Inbox Assistant. Answer the user's question based on the provided emails.
        
        USER QUESTION: "{query}"
        
        INBOX CONTEXT:
        {email_context}
        
        INSTRUCTIONS:
        - Answer directly based on the emails.
        - Cite the sender or subject if relevant.
        - If the answer is not in the emails, say "I couldn't find that information in your recent emails."
        - Be concise and helpful.
        """
        
        try:
            if self.client:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text
            else:
                 return "AI Client not initialized."
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                 return "⚠️ I'm currently offline due to high traffic (Quota Exceeded). But don't worry, your emails are safe! (Mock: I found 3 emails about that topic...)"
            return f"I encountered an error analyzing your inbox: {e}"
