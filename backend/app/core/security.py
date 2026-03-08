"""Security helpers.

Token issuance and validation is now fully delegated to Keycloak (OIDC).
This module only retains the password-hashing utility which may still be
used for locally-managed service accounts, or can be removed entirely if
all user management is done through Keycloak.
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
