from tortobaza.finance_db import current_finance_db, route_all_models

_LEDGER_MODELS = {
    "financialaccount",
    "financialtransaction",
    "financialtransactionrule",
    "financialtransactionrulecondition",
}

_DEFAULT_ONLY_MODELS = {
    "cardsmsmessage",
}


def _is_ledger(model) -> bool:
    if model._meta.app_label != "crm":
        return False
    if model._meta.model_name in _LEDGER_MODELS:
        return True
    auto_created = model._meta.auto_created
    return bool(auto_created) and auto_created._meta.model_name == "financialtransaction"


def _db_for(model):
    if route_all_models() or _is_ledger(model):
        return current_finance_db()
    return None


class FinanceRouter:
    def db_for_read(self, model, **hints):
        return _db_for(model)

    def db_for_write(self, model, **hints):
        return _db_for(model)

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "crm" and model_name in _DEFAULT_ONLY_MODELS:
            return db == "default"
        return None
