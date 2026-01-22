import os
import mysql.connector
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Database Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "agent_db")
SSL_CA = os.getenv("SSL_CA")

# Sanitize SSL path logic (same as app)
if SSL_CA:
    SSL_CA = SSL_CA.strip('"').strip("'")
    if not os.path.exists(SSL_CA):
        # Fallback to local cert if not found (dev env)
        fallback = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DigiCertGlobalRootG2.crt.pem")
        if os.path.exists(fallback):
            SSL_CA = fallback

print(f"Connecting to {DB_HOST}...")

try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        ssl_ca=SSL_CA,
        ssl_verify_cert=True,
        use_pure=True
    )
    cursor = conn.cursor()

    # 1. Add user_email to meeting table
    try:
        print("Adding user_email to 'meeting' table...")
        cursor.execute("ALTER TABLE meeting ADD COLUMN user_email VARCHAR(255);")
        print("Success: Added user_email to meeting.")
    except mysql.connector.Error as err:
        if "Duplicate column name" in str(err):
            print("Info: user_email already exists in meeting.")
        else:
            print(f"Error updating meeting table: {err}")

    # 2. Add user_email to chathistory table
    try:
        print("Adding user_email to 'chathistory' table...")
        cursor.execute("ALTER TABLE chathistory ADD COLUMN user_email VARCHAR(255);")
        print("Success: Added user_email to chathistory.")
    except mysql.connector.Error as err:
        if "Duplicate column name" in str(err):
            print("Info: user_email already exists in chathistory.")
        else:
            print(f"Error updating chathistory table: {err}")

    conn.commit()
    cursor.close()
    conn.close()
    print("Migration completed.")

except Exception as e:
    print(f"Connection Failed: {e}")
