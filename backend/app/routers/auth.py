from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.audit import log_action
from app.auth import create_access_token, verify_password
from app.database import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas import LoginResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


@router.post("/login", response_model=LoginResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == form_data.username)).first()

    if user is not None and user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked until {user.locked_until.isoformat()}Z due to repeated failed logins. "
            "Try again later.",
        )

    valid = bool(user) and user.active and verify_password(form_data.password, user.hashed_password)

    if not valid:
        if user is not None:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
                session.add(user)
                session.commit()
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many failed login attempts. Account locked for {LOCKOUT_MINUTES} minutes.",
                )
            session.add(user)
            session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    user.failed_login_attempts = 0
    user.locked_until = None
    session.add(user)
    session.commit()

    log_action(session, user, "auth.login", "User", user.id, {"username": user.username})

    token = create_access_token(subject=user.username)
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    # JWTs are stateless in this demo (no revocation/blocklist) — the token
    # remains valid until it expires. This endpoint exists purely to record
    # the audit trail entry; the frontend still discards the token locally.
    log_action(session, user, "auth.logout", "User", user.id, {"username": user.username})
