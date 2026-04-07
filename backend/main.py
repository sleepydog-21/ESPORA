from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta
import smtplib
from email.message import EmailMessage

import models
import schemas
import auth
from routes import users, sites, cases, fields, globals, sessions, webhooks
from database import get_db, engine
from config import settings
import scheduler

app = FastAPI(title="ESPORA Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(sites.router)
app.include_router(cases.router)
app.include_router(fields.router)
app.include_router(globals.router)
app.include_router(sessions.router)
app.include_router(webhooks.router)

@app.on_event("startup")
def startup_event():
    scheduler.start_scheduler()

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": user.email, "role": user.role.value, "site_id": user.site_id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user

# Dummy route to test email functionality
@app.post("/test-email")
def test_email(to_email: str):
    msg = EmailMessage()
    msg.set_content(f"This is a test email sent from ESPORA Platform.")
    msg['Subject'] = 'Test Email'
    msg['From'] = settings.mail_sender
    msg['To'] = to_email

    try:
        with smtplib.SMTP(settings.mail_server, settings.mail_port) as server:
            server.send_message(msg)
        return {"msg": "Email sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
