import argparse
import json
import datetime
from agent import MailAgent, Email

def main():
    parser = argparse.ArgumentParser(description="AI Mail Intelligence Agent CLI")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument("--sender", required=True, help="Sender email address")
    parser.add_argument("--body", required=True, help="Email body content")
    parser.add_argument("--prompt-path", default="prompt.txt", help="Path to the system prompt file")

    args = parser.parse_args()

    # Create Email object
    # For this CLI, we assume 'now' as received time, or could be added as arg
    received_time = datetime.datetime.now().isoformat()
    
    email = Email(
        subject=args.subject,
        sender=args.sender,
        received_time=received_time,
        body_preview=args.body[:500] # Truncate as per instructions
    )

    # Initialize Agent
    try:
        agent = MailAgent(prompt_path=args.prompt_path)
    except FileNotFoundError as e:
        print(json.dumps({"error": str(e)}))
        return

    # Analyze
    result = agent.analyze_email(email)

    # Output JSON
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
