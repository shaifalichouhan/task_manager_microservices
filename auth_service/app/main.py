# auth_service/app/main.py
from fastapi import FastAPI
from sqlalchemy.exc import OperationalError
import time
from app.core.database import Base, engine
from app.routers import auth as auth_router

app = FastAPI()

app.include_router(auth_router.router)

@app.on_event("startup")
def startup():
    retries = 8
    delay = 3
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            print("DB tables created/confirmed")
            break
        except OperationalError as e:
            print(f"DB not ready (attempt {attempt}/{retries}): {e}")
            if attempt == retries:
                raise
            time.sleep(delay)
