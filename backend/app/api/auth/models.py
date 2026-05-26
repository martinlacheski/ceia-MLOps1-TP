from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    username: str
    full_name: str
    permissions: list[str]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthenticatedUser
