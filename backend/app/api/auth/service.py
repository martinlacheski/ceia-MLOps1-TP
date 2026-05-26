from app.api.auth.models import AuthenticatedUser
from app.core.config import settings
from app.core.security import hash_password, verify_password


# Usuario de desarrollo para la primera iteración.
# Más adelante se reemplaza por base de datos y migraciones.
_DEV_USER_PASSWORD_HASH = hash_password(settings.demo_password)

_DEV_USER = AuthenticatedUser(
    username=settings.demo_username,
    full_name=settings.demo_full_name,
    permissions=["prediction:read"],
)


def authenticate_user(username: str, password: str) -> AuthenticatedUser | None:
    if username != _DEV_USER.username:
        return None

    if not verify_password(password, _DEV_USER_PASSWORD_HASH):
        return None

    return _DEV_USER


def get_user_by_username(username: str) -> AuthenticatedUser | None:
    if username != _DEV_USER.username:
        return None
    return _DEV_USER
