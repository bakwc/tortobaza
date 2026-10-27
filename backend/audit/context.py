from contextvars import ContextVar, Token

from django.contrib.auth.models import User
from django.db.models import Model

_actor: ContextVar[User | None] = ContextVar("audit_actor", default=None)
_pending: ContextVar[dict | None] = ContextVar("audit_pending", default=None)


def bind(user: User | None) -> tuple[Token, Token]:
    return _actor.set(user), _pending.set({})


def release(tokens: tuple[Token, Token]) -> None:
    actor_token, pending_token = tokens
    _actor.reset(actor_token)
    _pending.reset(pending_token)


def current_actor() -> User | None:
    return _actor.get()


def pending_bucket() -> dict | None:
    return _pending.get()


def database_of(instance: Model) -> str:
    db = instance._state.db
    if not db:
        return "default"
    return db
