import secrets

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from betteru.deps import DB, CurrentUser
from betteru.models import User
from betteru.schemas import LoginIn, RegisterIn, UserOut
from betteru.security import clear_session_cookie, hash_password, set_session_cookie, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Device accounts: no email or password. The account lives as long as this
# browser keeps its cookie (~10 years), so it behaves like local app data.
DEVICE_DOMAIN = "device.invalid"  # .invalid is a reserved TLD: never a real address
DEVICE_SESSION_DAYS = 3650


def user_out(user: User) -> UserOut:
    email = "" if user.email.endswith("@" + DEVICE_DOMAIN) else user.email
    return UserOut(id=user.id, email=email, name=user.name, has_profile=user.profile is not None)


@router.post("/device", response_model=UserOut, status_code=201)
def create_device_account(response: Response, db: DB):
    """Create an account for this device and sign it in. Used instead of sign-up while
    BetterU runs privately; email/password sign-up below stays available for later."""
    user = User(email=f"device-{secrets.token_hex(12)}@{DEVICE_DOMAIN}", password_hash="!", name="")
    db.add(user)
    db.commit()
    db.refresh(user)
    set_session_cookie(response, user.id, days=DEVICE_SESSION_DAYS)
    return user_out(user)


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn, response: Response, db: DB):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(email=email, password_hash=hash_password(body.password), name=body.name.strip())
    db.add(user)
    db.commit()
    db.refresh(user)
    set_session_cookie(response, user.id)
    return user_out(user)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: DB):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    set_session_cookie(response, user.id)
    return user_out(user)


@router.post("/logout", status_code=204)
def logout(response: Response):
    clear_session_cookie(response)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user_out(user)
