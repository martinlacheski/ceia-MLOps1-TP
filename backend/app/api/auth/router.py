from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.auth.models import AuthenticatedUser, TokenResponse
from app.api.auth.service import authenticate_user
from app.core.dependencies import CurrentUser
from app.core.security import create_access_token


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    user = authenticate_user(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user.username, "permissions": user.permissions})
    return TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=AuthenticatedUser)
def get_me(current_user: CurrentUser) -> AuthenticatedUser:
    return current_user
