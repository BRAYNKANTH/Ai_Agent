from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv
import os

load_dotenv()
from sqlmodel import SQLModel, create_engine, Session

# Default to SQLite if DB_HOST not set, but prefer MySQL
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "3306")
db_user = os.getenv("DB_USER", "root")
db_password = os.getenv("DB_PASSWORD", "")
db_name = os.getenv("DB_NAME", "users_db")

mysql_url = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# SSL Configuration
connect_args = {"use_pure": True} # Force pure Python to avoid C-ext SSL errors
ssl_ca = os.getenv("SSL_CA")

# Fallback: Try to find cert relative to this file if env var path fails
if ssl_ca and not os.path.exists(ssl_ca):
    # Check parent directory (backend root)
    candidate = os.path.join(os.path.dirname(__file__), "..", os.path.basename(ssl_ca))
    if os.path.exists(candidate):
        ssl_ca = candidate

if ssl_ca:
    connect_args["ssl_ca"] = ssl_ca
    connect_args["ssl_verify_cert"] = True

# Use MySQL if env var is set or default string is valid, else fallback
# For this migration, we assume user will provide DB
engine = create_engine(mysql_url, echo=True, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
