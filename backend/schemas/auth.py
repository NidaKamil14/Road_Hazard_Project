from typing import Annotated, Optional
from pydantic import BaseModel, StringConstraints, Field

Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Password = Annotated[str, StringConstraints(min_length=1, max_length=256)]

class AuthUser(BaseModel):
    username: Username

class LoginRequest(BaseModel):
    username: Username = Field(description="Administrator username")
    password: Password = Field(description="Administrator password")

class LoginResponse(BaseModel):
    success: bool
    user: AuthUser

class SessionResponse(BaseModel):
    authenticated: bool
    user: Optional[AuthUser] = None
