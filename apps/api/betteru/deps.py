from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from betteru.db import get_db
from betteru.models import User
from betteru.security import COOKIE_NAME, decode_token

DB = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DB,
    session: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> User:
    user_id = decode_token(session) if session else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
