import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Load configuration from the local .env file.
load_dotenv()

# Read the database URL from the environment.
# Fall back to a local SQLite database if it is not configured.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./network_management.db",
)

# SQLite needs this setting when connections are used
# across different threads, as can happen in web applications.
connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# Create the SQLAlchemy engine.
# The engine manages the underlying database connections.
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

# Each request can create its own database session.
# Sessions are used to query and update database records.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class used by our SQLAlchemy database models.
Base = declarative_base()


def get_db():
    """
    Provide a database session to an API endpoint.

    The session is always closed after the request finishes,
    including when an exception occurs.
    """

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()