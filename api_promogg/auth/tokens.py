import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4


def generate_opaque_token(nbytes: int = 32) -> str:
    if nbytes < 32:
        raise ValueError("Tokens opacos devem ter pelo menos 32 bytes de entropia.")
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    if not token:
        raise ValueError("Token obrigatório.")
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def compare_token(token: str, stored_hash: str) -> bool:
    if not token or not stored_hash:
        return False
    try:
        candidate = hash_token(token)
    except ValueError:
        return False
    return secrets.compare_digest(candidate, stored_hash)


@dataclass
class RefreshTokenRecord:
    id: str
    token_hash: str
    family_id: str
    previous_token_id: str | None = None
    used_at: datetime | None = None
    revoked_at: datetime | None = None
    reuse_detected_at: datetime | None = None


@dataclass
class RefreshRotationResult:
    status: str
    token: str | None = None
    record: RefreshTokenRecord | None = None


class InMemoryRefreshTokenStore:
    """Simulação isolada de refresh token rotativo para testes de segurança."""

    def __init__(self):
        self.records: list[RefreshTokenRecord] = []

    def issue_initial(self) -> tuple[str, RefreshTokenRecord]:
        token = generate_opaque_token()
        record = RefreshTokenRecord(
            id=f"rt_{uuid4().hex}",
            token_hash=hash_token(token),
            family_id=f"rtf_{uuid4().hex}",
        )
        self.records.append(record)
        return token, record

    def rotate(self, token: str) -> RefreshRotationResult:
        record = self._find_by_token(token)
        if record is None:
            return RefreshRotationResult(status="invalid")

        if record.used_at is not None or record.revoked_at is not None:
            self._mark_reuse(record)
            return RefreshRotationResult(status="reused", record=record)

        now = datetime.now(UTC)
        record.used_at = now
        new_token = generate_opaque_token()
        new_record = RefreshTokenRecord(
            id=f"rt_{uuid4().hex}",
            token_hash=hash_token(new_token),
            family_id=record.family_id,
            previous_token_id=record.id,
        )
        self.records.append(new_record)
        return RefreshRotationResult(status="rotated", token=new_token, record=new_record)

    def _find_by_token(self, token: str) -> RefreshTokenRecord | None:
        for record in self.records:
            if compare_token(token, record.token_hash):
                return record
        return None

    def _mark_reuse(self, record: RefreshTokenRecord):
        now = datetime.now(UTC)
        record.reuse_detected_at = now
        for item in self.records:
            if item.family_id == record.family_id and item.revoked_at is None:
                item.revoked_at = now
