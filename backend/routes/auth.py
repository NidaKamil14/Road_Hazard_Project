from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.admin import Admin
from backend.schemas.auth import LoginRequest, LoginResponse, SessionResponse, AuthUser
from pwdlib import PasswordHash

router = APIRouter(prefix="/auth", tags=["auth"])
password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("dummy_password_for_timing_mitigation")

@router.post("/login", response_model=LoginResponse)
def login(login_data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == login_data.username).first()

    invalid_creds_exc = HTTPException(
        status_code=401,
        detail="invalid_credentials",
    )

    if not admin or not admin.is_active:
        password_hash.verify(login_data.password, DUMMY_PASSWORD_HASH)
        raise invalid_creds_exc

    if not password_hash.verify(login_data.password, admin.password_hash):
        raise invalid_creds_exc

    request.session.clear()
    request.session["admin_id"] = admin.admin_id
    request.session["username"] = admin.username

    return LoginResponse(success=True, user=AuthUser(username=admin.username))

@router.get("/session", response_model=SessionResponse)
def get_session(request: Request, db: Session = Depends(get_db)):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return SessionResponse(authenticated=False)

    admin = db.query(Admin).filter(Admin.admin_id == admin_id).first()
    if not admin or not admin.is_active:
        request.session.clear()
        raise HTTPException(
            status_code=401,
            detail="invalid_credentials",
        )

    return SessionResponse(
        authenticated=True,
        user=AuthUser(username=admin.username)
    )

@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"success": True}
