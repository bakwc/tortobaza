from contextlib import contextmanager
from contextvars import ContextVar

_finance_db: ContextVar[str] = ContextVar("finance_db", default="default")
_route_all: ContextVar[bool] = ContextVar("finance_route_all", default=False)


def current_finance_db() -> str:
    return _finance_db.get()


def route_all_models() -> bool:
    return _route_all.get()


@contextmanager
def use_finance_db(alias: str):
    token = _finance_db.set(alias)
    try:
        yield
    finally:
        _finance_db.reset(token)


@contextmanager
def use_migration_db(alias: str):
    db_token = _finance_db.set(alias)
    route_token = _route_all.set(True)
    try:
        yield
    finally:
        _route_all.reset(route_token)
        _finance_db.reset(db_token)
