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

# SSL Configuration for Azure MySQL
connect_args = {}
ssl_ca = os.getenv("SSL_CA") # e.g., "backend/DigiCertGlobalRootCA.crt.pem" or absolute path
if ssl_ca:
    connect_args["ssl_ca"] = ssl_ca
    connect_args["ssl_verify_cert"] = True

# Use MySQL if env var is set or default string is valid, else fallback (though here we hard switch)
# For this migration, we assume user will provide DB
engine = create_engine(mysql_url, echo=True, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
