import json
import datetime
import os
from typing import Dict, Any, List, Optional
from sqlmodel import Session, select
from google import genai
from .meeting_models import Meeting
from .models import ChatHistory

class MeetingAgent:
    def __init__(self, session: Session, user_email: str):
        self.session = session
        self.user_email = user_email
        
        # Configure Gemini Client
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Error: GEMINI_API_KEY not found.")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)
            
        # Model definitions should be used in generate_content, ensuring we use a supported model
        self.model_name = "gemini-2.5-flash"

        self.system_prompt = """
        You are an intelligent AI Meeting Scheduling Agent that acts as a personal assistant.
        Your responsibility is to create, assign, check, update, and cancel meetings based strictly on natural language user input.

        Current Date: {current_date}

        You must return a JSON object with the following structure:
        {{
            "thought_process": "Short reasoning",
            "intent": "CREATE_MEETING" | "CHECK_MEETING" | "UPDATE_MEETING" | "DELETE_MEETING" | "GENERAL_QUERY" | "EXIT_TASK" | "ASK_INFO",
            "response_text": "Natural language response to the user",
            "action_payload": {{ ... details for action ... }}
        }}

        ACTION PAYLOADS:
        - CREATE_MEETING: {{ "title": "...", "start_time": "YYYY-MM-DD HH:MM:SS", "end_time": "YYYY-MM-DD HH:MM:SS", "participants": "..." }}
        - UPDATE_MEETING: {{ "original_meeting_id": null, "new_end_time": "...", "new_start_time": "..." }} 
        - CHECK_MEETING: {{ "date": "YYYY-MM-DD" }}
        - DELETE_MEETING: {{ "meeting_titles": ["Title1", "Title2"] }} 

        RULES:
        1. If missing info for creation (date, time), intent = ASK_INFO.
        2. If checking schedule and no date specified, assume TODAY.
        3. For DELETE_MEETING, provide the titles of the meetings to cancel in 'meeting_titles'. If user says "delete all" or "both", list them or try to identify them from context.
        4. If the user wants to perform TWO actions (e.g. "Delete X and Schedule Y"), prioritize the DELETE action first, and in your response ask for confirmation to proceed with creation. DO NOT attempt to do both.
        5. Be professional and helpful.
        """

    def process_message(self, user_message: str, conversation_history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        """
        Processes the user message using Gemini and returns a response and action.
        """
        current_date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Construct Prompt
        full_prompt = f"System: {self.system_prompt.format(current_date=current_date_str)}\n\n"
        
        for msg in conversation_history[-6:]:
            role = "User" if msg.get("sender") == "user" else "Assistant"
            full_prompt += f"{role}: {msg.get('text')}\n"
            
        full_prompt += f"User: {user_message}\nAssistant:"

        import time
        retries = 3
        delay = 10
        
        for attempt in range(retries):
            try:
                # Safety checks
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                
                if self.client:
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=full_prompt,
                        config={
                            'response_mime_type': 'application/json',
                            'safety_settings': safety_settings
                        }
                    )
                else:
                    raise Exception("Gemini Client not initialized")
                
                # Debug: Print raw response
                print(f"DEBUG LLM Raw Response: {response.text}")
                
                content = response.text
                content = content.replace("```json", "").replace("```", "").strip()
                
                try:
                    start_idx = content.find('{')
                    end_idx = content.rfind('}')
                    if start_idx != -1 and end_idx != -1:
                        content = content[start_idx : end_idx + 1]
                    data = json.loads(content)
                    break # Success, exit retry loop
                    
                except json.JSONDecodeError:
                    print("JSON Decode Failed. Raw content:", content)
                    return {"response": "I understood, but I'm having trouble processing the details internally. Could you say that again?", "action": "ERROR"}

            except Exception as e:
                 error_str = str(e)
                 if "429" in error_str or "quota" in error_str.lower():
                     print(f"⚠️ MeetingAgent Quota Handler: Hit 429. Waiting {delay}s (Attempt {attempt+1}/{retries})...")
                     time.sleep(delay)
                     delay *= 2 
                 else:
                     print(f"LLM Error: {e}")
                     return {"response": "I'm having trouble connecting to my brain right now. Please try again.", "action": "ERROR"}
        
        else:
             # Loop completed without break = failed all retries
             print("❌ MeetingAgent Quota Retries Exhausted.")
             return {"response": "I'm currently overwhelmed with requests. Please try again in a minute.", "action": "ERROR"}
            
        intent = data.get("intent")
        response_text = data.get("response_text")
        payload = data.get("action_payload", {})
        
        # Execute Action
        if intent == "CREATE_MEETING":
            result = self._create_meeting(payload)
            if result: response_text = result 
            
        elif intent == "CHECK_MEETING":
            check_date = payload.get("date")
            result_text = self._check_meetings(check_date)
            response_text = result_text 
            
        elif intent == "UPDATE_MEETING":
            result = self._update_last_meeting(payload)
            if result: response_text = result

        elif intent == "DELETE_MEETING":
            result = self._delete_meetings(payload)
            if result: response_text = result

        # Persist Chat History
        self.session.add(ChatHistory(sender="user", text=user_message, user_email=self.user_email))
        self.session.add(ChatHistory(sender="agent", text=response_text, user_email=self.user_email))
        self.session.commit()

        return {"response": response_text, "action": intent}



    def _create_meeting(self, payload):
        try:
            title = payload.get("title", "Meeting")
            start_str = payload.get("start_time")
            end_str = payload.get("end_time")
            participants = payload.get("participants", "")
            
            start_dt = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S") if end_str else start_dt + datetime.timedelta(hours=1)
            
            # Check for conflicts
            # Overlap if: (StartA < EndB) and (EndA > StartB)
            stmt = select(Meeting).where(
                Meeting.user_email == self.user_email,
                Meeting.status == "scheduled",
                Meeting.start_time < end_dt,
                Meeting.end_time > start_dt
            )
            conflicts = self.session.exec(stmt).all()
            
            if conflicts:
                conflict_titles = [m.title for m in conflicts]
                return f"⚠️ Conflict detected! You already have {len(conflicts)} meeting(s) scheduled at that time: {', '.join(conflict_titles)}. Please choose a different time."

            new_meeting = Meeting(
                title=title,
                start_time=start_dt,
                end_time=end_dt,
                participants=participants,
                status="scheduled",
                user_email=self.user_email
            )
            self.session.add(new_meeting)
            self.session.commit()
            start_fmt = start_dt.strftime('%I:%M %p')
            return f"Scheduled: {title} on {start_dt.date()} at {start_fmt}."
        except Exception as e:
            print(f"Create Error: {e}")
            return None 

    def _check_meetings(self, date_str):
        try:
            if not date_str: date_str = datetime.date.today().isoformat()
            target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            
            stmt = select(Meeting).where(Meeting.user_email == self.user_email, Meeting.status == "scheduled")
            all_meetings = self.session.exec(stmt).all()
            day_meetings = [m for m in all_meetings if m.start_time.date() == target_date]
            
            if not day_meetings:
                 return f"Your schedule looks clear for {target_date.strftime('%A, %B %d')}."
            
            resp = f"Here is your schedule for {target_date.strftime('%A, %B %d')}:\n"
            for m in day_meetings:
                start_str = m.start_time.strftime("%I:%M %p")
                end_str = m.end_time.strftime("%I:%M %p")
                resp += f"• {m.title} ({start_str} - {end_str})\n"
            return resp
        except Exception as e:
            return "I couldn't check the calendar."

    def _update_last_meeting(self, payload):
        try:
            stmt = select(Meeting).where(Meeting.user_email == self.user_email).order_by(Meeting.created_at.desc()).limit(1)
            last_meeting = self.session.exec(stmt).first()
            if not last_meeting: return "No meeting found to update."
            
            if payload.get("new_end_time"):
                 last_meeting.end_time = datetime.datetime.strptime(payload.get("new_end_time"), "%Y-%m-%d %H:%M:%S")
            if payload.get("new_start_time"):
                 last_meeting.start_time = datetime.datetime.strptime(payload.get("new_start_time"), "%Y-%m-%d %H:%M:%S")
                 
            self.session.add(last_meeting)
            self.session.commit()
            return f"Updated {last_meeting.title}."
        except:
            return None

    def _delete_meetings(self, payload) -> str:
        """
        Deletes meetings based on titles provided in payload.
        Falls back to last created if no titles.
        """
        try:
            titles = payload.get("meeting_titles", [])
            
            # Handle string input just in case
            if isinstance(titles, str):
                titles = [titles]
            
            deleted_names = []

            if titles:
                # Delete by title
                for title_query in titles:
                    # Case-insensitive partial match
                    stmt = select(Meeting).where(
                        Meeting.user_email == self.user_email, 
                        Meeting.title.ilike(f"%{title_query}%"), 
                        Meeting.status == "scheduled"
                    )
                    matches = self.session.exec(stmt).all()
                    
                    for m in matches:
                        self.session.delete(m)
                        deleted_names.append(m.title)
                
                self.session.commit()
                if deleted_names:
                    return f"Successfully cancelled: {', '.join(deleted_names)}."
                else:
                    return f"I couldn't find any scheduled meetings matching: {', '.join(titles)}."
            else:
                # Fallback: Delete last created
                stmt = select(Meeting).where(Meeting.user_email == self.user_email, Meeting.status == "scheduled").order_by(Meeting.created_at.desc()).limit(1)
                last = self.session.exec(stmt).first()
                if last:
                    self.session.delete(last)
                    self.session.commit()
                    return f"Cancelled your last scheduled meeting: {last.title}."
                else:
                    return "You have no scheduled meetings to cancel."

        except Exception as e:
            print(f"Delete Error: {e}")
            return "Failed to cancel the meeting(s) due to an error."
