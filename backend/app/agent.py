import json
import os
import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Email:
    def __init__(self, subject: str, sender: str, received_time: str, body_preview: str, body: str = None):
        self.subject = subject
        self.sender = sender
        self.received_time = received_time
        self.body_preview = body_preview
        self.body = body

    def to_string(self) -> str:
        content = self.body if self.body else self.body_preview
        return (
            f"Subject: {self.subject}\n"
            f"Sender: {self.sender}\n"
            f"ReceivedTime: {self.received_time}\n"
            f"Body: {content}\n"
        )

class EmailAnalysis(BaseModel):
    intent: str = Field(description="The primary intent of the email (e.g., 'Meeting Request', 'System Alert', 'Newsletter').")
    urgency_score: int = Field(description="A score from 1 (Low) to 5 (Critical) indicating how urgent the email is.")
    risk_level: str = Field(description="Risk assessment: 'Low', 'Medium', 'High'.")
    priority: str = Field(description="Priority label: 'P1' (Critical), 'P2' (High), 'P3' (Normal), 'P4' (Low).")
    requires_action: bool = Field(description="True if the user needs to perform an action, False otherwise.")
    suggested_actions: List[str] = Field(description="A list of recommended actions for the user.")
    summary: str = Field(description="A concise one-sentence summary of the email content.")

class MailAgent:
    def __init__(self, prompt_path: str = "prompt.txt"):
        self.prompt_path = prompt_path
        from google import genai
        
        # Configure Gemini Client
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("WARNING: GEMINI_API_KEY not found in env")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)
            
        self.model_name = "gemini-2.5-flash"

        self.system_prompt = """
        You are an elite AI Executive Assistant. Analyze the email explicitly based on the FULL BODY content provided. 
        
        Extract/Generate:
        1. **intent**: "Meeting Request", "System Alert", "Personal", "Newsletter", etc.
        2. **urgency_score**: 1 (Low) to 5 (Critical).
        3. **risk_level**: "Low", "Medium", "High" (Spam/Phishing).
        4. **priority**: "P1" (Critical) to "P4" (Low).
        5. **requires_action**: Boolean.
        6. **suggested_actions**: List of strings (e.g. "Reply", "Archive").
        7. **summary**: MAX 10 WORDS. Focus on the 'what' and 'deadline'. No "This email is about...".
        8. **suggested_reply**: A professional, complete, contextual reply ready to send. DO NOT use placeholders like "[Your Name]". Sign off as "Best,". Ensure the tone matches the context. If no reply is needed, return null.
        9. **sentiment**: "Positive", "Neutral", "Negative".
        10. **tone**: "Formal", "Casual", "Urgent", "Friendly".
        """

    def analyze_email(self, email: Email) -> Dict[str, Any]:
        """
        Analyzes the email using Real Gemini API.
        """
        prompt = f"{self.system_prompt}\n\n📌 INPUT EMAIL\n\n{email.to_string()}\n\n📌 OUTPUT JSON"
        
        import time
        retries = 3
        delay = 10
        
        for attempt in range(retries):
            try:
                if not self.client:
                     return self._mock_llm_response(email)
                    
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config={'response_mime_type': 'application/json'}
                )
                return self._validate_and_parse(response.text)
            except Exception as e:
                 error_str = str(e)
                 if "429" in error_str or "quota" in error_str.lower():
                     print(f"⚠️ Gemini Quota Handler: Hit 429. Waiting {delay}s (Attempt {attempt+1}/{retries})...")
                     time.sleep(delay)
                     delay *= 2 # 10s, 20s, 40s
                 else:
                     print(f"Gemini Error: {e}")
                     return self._mock_llm_response(email)
        
        print("❌ Gemini Quota Retries Exhausted.")
        return self._mock_llm_response(email)

    def _validate_and_parse(self, response_text: str) -> Dict[str, Any]:
        try:
            # Clean markdown code blocks if present
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            print(f"Failed to parse JSON: {response_text}")
            return self._mock_llm_response(None)

    def _mock_llm_response(self, email: Optional[Email]) -> Dict[str, Any]:
         return {
            "intent": "Error Fallback",
            "urgency_score": 1,
            "risk_level": "Low",
            "priority": "P4",
            "requires_action": False,
            "suggested_actions": [],
            "summary": "Failed to analyze email.",
            "suggested_reply": None,
            "sentiment": "Neutral",
            "tone": "Neutral"
        }

    def rewrite_email(self, text: str, style: str) -> str:
        """
        Rewrites the given email text based on the requested style.
        Possible styles: 'formal', 'casual', 'shorten', 'fix_grammar'.
        """
        prompt = f"""
        You are an elite AI Editor. Rewrite the following email draft.
        
        GOAL: Make it {style}.
        
        RULES:
        - Keep the core meaning.
        - Return ONLY the rewritten text. No "Here is the rewritten email:" prefix.
        - If 'fix_grammar', just correct errors.
        - If 'shorten', concise it significantly.

        DRAFT:
        {text}
        
        REWRITTEN:
        """
        
        try:
             # Use a simple generation config for plain text
            if not self.client:
                raise Exception("Client not initialized")
                
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={"response_mime_type": "text/plain"}
            )
            return response.text.strip()
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                print(f"Gemini Quota Exceeded. Using Mock Fallback.")
                # Fallback mock for demonstration when API is down
                if style == "formal":
                    return f"Subject: Regarding your recent inquiry\n\nDear recipient,\n\n{text}\n\nSincerely,\n[Your Name]"
                elif style == "shorten":
                    return f"(TL;DR Version): {text[:50]}..."
                elif style == "casual":
                    return f"Hey!\n\n{text}\n\nCheers!"
                else:
                    return f"[Fixed Grammar]: {text}"
            
            print(f"Gemini Rewrite Error: {e}")
            return f"[Error generating rewrite: {str(e)}]"

            print(f"Gemini Rewrite Error: {e}")
            return f"[Error generating rewrite: {str(e)}]"

    def _validate_and_parse(self, json_str: str) -> Dict[str, Any]:
        try:
            # Clean Markdown
            cleaned = json_str.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            data = json.loads(cleaned.strip())
            
            # Basic validation
            if "suggested_reply" not in data: data["suggested_reply"] = None
            return data
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            print(f"Raw Output: {json_str}")
            return {"error": "Failed to parse JSON"}
        except ValueError as e:
            return {"error": str(e)}

if __name__ == "__main__":
    # Test
    agent = MailAgent()
    sample_email = Email(
        subject="Urgent: Server Down",
        sender="monitoring@example.com",
        received_time="2025-10-27T10:00:00",
        body_preview="The main production server is not responding. Please investigate immediately."
    )
    result = agent.analyze_email(sample_email)
    print(json.dumps(result, indent=2))
