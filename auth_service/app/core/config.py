import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
    SECRET_KEY = os.getenv("SECRET_KEY", "5b719394-024f-43d0-b15e-5a11d2f5b5a1")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    def __init__(self):
        # Debug: Print what we're getting
        print(f"DATABASE_URL from env: {self.DATABASE_URL}")
        
        # Fallback if not found
        if not self.DATABASE_URL:
            self.DATABASE_URL = "postgresql+psycopg2://postgres:postgres@postgres_db:5432/task_manager"
            print(f"Using fallback DATABASE_URL: {self.DATABASE_URL}")

settings = Settings()