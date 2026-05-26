from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.api.auth.models import AuthenticatedUser
from app.api.auth.service import get_user_by_username
from app.core.security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> AuthenticatedUser:
    payload = decode_access_token(token)
    data = payload.get("data", {})
    username = data.get("sub")

    if not isinstance(username, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado")

    user = get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado")

    return user


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, user: CurrentUser) -> AuthenticatedUser:
        if self.required_permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permisos suficientes para esta acción",
            )
        return user
