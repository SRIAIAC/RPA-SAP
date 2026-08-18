from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.auth import decode_token
from app.database import get_session
from app.models import LEVEL_RANK, Level, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    username = decode_token(token)
    if username is None:
        raise credentials_exception
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None or not user.active:
        raise credentials_exception
    return user


def require_min_level(min_level: Level):
    def checker(user: User = Depends(get_current_user)) -> User:
        if LEVEL_RANK[user.level] < LEVEL_RANK[min_level]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires at least '{min_level.value}' level",
            )
        return user

    return checker


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.level != Level.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
