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
db_name = os.getenv("DB_NAME", "agent_db") # Using same DB for now/simplicity

mysql_url = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# SSL Configuration for Azure MySQL
connect_args = {}
ssl_ca = os.getenv("SSL_CA")
if ssl_ca:
    connect_args["ssl_ca"] = ssl_ca
    connect_args["ssl_verify_cert"] = True

engine = create_engine(mysql_url, echo=True, connect_args=connect_args)

def create_meeting_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_meeting_session():
    with Session(engine) as session:
        yield session
