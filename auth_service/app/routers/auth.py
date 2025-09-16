from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from app.core.database import get_db
from app.models.user import User, UserTypeEnum
from app.schemas.user import UserCreate, UserOut, Token
from app.utils.security import get_password_hash, verify_password, create_access_token, decode_token
from app.core.config import settings
import json
import pika

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def publish_user_registered(user_id: int, email: str):
    try:
        params = pika.URLParameters(settings.RABBITMQ_URL)
        conn = pika.BlockingConnection(params)
        ch = conn.channel()
        ch.exchange_declare(exchange="events", exchange_type="topic", durable=True)
        msg = json.dumps({"event": "user.registered", "user_id": user_id, "email": email})
        ch.basic_publish(exchange="events", routing_key="user.registered", body=msg)
        conn.close()
    except Exception:
        # swallow or log in production; don't let publish break registration
        pass

@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = get_password_hash(user_in.password)
    user = User(email=user_in.email, hashed_password=hashed, user_type=UserTypeEnum(user_in.user_type))
    db.add(user)
    db.commit()
    db.refresh(user)

    # publish event for other services (notification_service etc.)
    publish_user_registered(user.id, user.email)

    return user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    token = create_access_token({"sub": str(user.id), "user_type": user.user_type.value})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/verify", response_model=UserOut)
def verify(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token)
    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
