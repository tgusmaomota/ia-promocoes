from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerifyMismatchError, VerificationError


_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Senha obrigatória.")
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    if not password_hash:
        return True
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True
