from django.apps import apps
from django.contrib.auth.models import Group, Permission
from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import SectionAccess

CATALOG_SECTION_ACTIONS = {
    "view_catalog": ("view",),
    "edit_catalog": ("view", "add", "change", "delete"),
}


def section_codenames() -> set[str]:
    return {code for code, _name in SectionAccess._meta.permissions}


EXPLICIT_SECTION_CODES = {"require_ready_photo"}


def has_explicit_section_perm(user, codename: str) -> bool:
    if user.user_permissions.filter(
        content_type__app_label="accounts",
        content_type__model="sectionaccess",
        codename=codename,
    ).exists():
        return True
    return user.groups.filter(
        permissions__content_type__app_label="accounts",
        permissions__content_type__model="sectionaccess",
        permissions__codename=codename,
    ).exists()


def requires_ready_photo(user) -> bool:
    return has_explicit_section_perm(user, "require_ready_photo")


def user_section_codes(user) -> list[str]:
    prefix = "accounts."
    known = section_codenames()
    codes = []
    for perm in user.get_all_permissions():
        if not perm.startswith(prefix):
            continue
        code = perm[len(prefix):]
        if code in known:
            codes.append(code)
    if user.is_superuser:
        codes = [
            code
            for code in codes
            if code not in EXPLICIT_SECTION_CODES or has_explicit_section_perm(user, code)
        ]
    return sorted(codes)


def permission_rows() -> list[dict[str, str]]:
    return [{"code": code, "label": str(name)} for code, name in SectionAccess._meta.permissions]


def admin_model_permissions(codes: list[str]) -> list[Permission]:
    actions: set[str] = set()
    for code in codes:
        for action in CATALOG_SECTION_ACTIONS.get(code, ()):
            actions.add(action)
    if not actions:
        return []
    codenames = [
        f"{action}_{model._meta.model_name}"
        for model in apps.get_app_config("catalog").get_models()
        for action in actions
    ]
    perms = list(
        Permission.objects.filter(
            content_type__app_label="catalog",
            codename__in=codenames,
        )
    )
    if len(perms) != len(codenames):
        raise RuntimeError("Catalog model permissions are missing.")
    return perms


def can_view(user, section: str) -> bool:
    return (
        user.has_perm(f"accounts.view_{section}")
        or user.has_perm(f"accounts.edit_{section}")
        or user.has_perm(f"accounts.edit_own_{section}")
    )


def can_edit(user, section: str) -> bool:
    return user.has_perm(f"accounts.edit_{section}")


def can_change_finished(user, document) -> bool:
    if user.has_perm("accounts.edit_finished"):
        return True
    if not user.has_perm("accounts.edit_own_finished"):
        return False
    if document is None:
        return True
    return document.created_by_id == user.id


def can_see_costs(user) -> bool:
    return bool(user.is_authenticated and user.has_perm("accounts.view_costs"))


def _order_party(fulfillment_type: str) -> str:
    if fulfillment_type == "pickup":
        return "pickup"
    return "delivery"


def can_see_order_address(user, fulfillment_type: str) -> bool:
    if can_edit(user, "orders"):
        return True
    party = _order_party(fulfillment_type)
    return user.has_perm(f"accounts.view_order_{party}_address")


def can_see_order_contacts(user, fulfillment_type: str) -> bool:
    if can_edit(user, "orders"):
        return True
    party = _order_party(fulfillment_type)
    return user.has_perm(f"accounts.view_order_{party}_contacts")


def can_see_order_price(user, fulfillment_type: str) -> bool:
    if can_edit(user, "orders"):
        return True
    party = _order_party(fulfillment_type)
    return user.has_perm(f"accounts.view_order_{party}_price")


ORDER_CONTACT_CHANGE_KEYS = ("contact", "nickname", "phones")
ORDER_ADDRESS_CHANGE_KEYS = ("delivery_address",)
ORDER_PRICE_CHANGE_KEYS = ("cake_price", "delivery_price", "prepayment", "payment_type")


def redact_order_field_changes(user, fulfillment_type: str | None, changes: dict) -> dict:
    redacted = {key: value for key, value in changes.items()}
    if fulfillment_type is None:
        hide_contacts = not (
            can_see_order_contacts(user, "delivery") and can_see_order_contacts(user, "pickup")
        )
        hide_address = not (
            can_see_order_address(user, "delivery") and can_see_order_address(user, "pickup")
        )
        hide_price = not (
            can_see_order_price(user, "delivery") and can_see_order_price(user, "pickup")
        )
    else:
        hide_contacts = not can_see_order_contacts(user, fulfillment_type)
        hide_address = not can_see_order_address(user, fulfillment_type)
        hide_price = not can_see_order_price(user, fulfillment_type)
    if hide_contacts:
        for key in ORDER_CONTACT_CHANGE_KEYS:
            redacted.pop(key, None)
    if hide_address:
        for key in ORDER_ADDRESS_CHANGE_KEYS:
            redacted.pop(key, None)
    if hide_price:
        for key in ORDER_PRICE_CHANGE_KEYS:
            redacted.pop(key, None)
    return redacted


ORDER_PARTY_CODES = (
    "view_order_delivery_address",
    "view_order_pickup_address",
    "view_order_delivery_contacts",
    "view_order_pickup_contacts",
    "view_order_delivery_price",
    "view_order_pickup_price",
)

_ORDER_STATUS_VALUES = (
    "unconfirmed",
    "new",
    "in_work",
    "ready",
    "client_approved",
    "in_delivery",
    "delivered",
)

ORDER_STATUS_CODES = tuple(
    f"set_order_{party}_status_{status}"
    for party in ("delivery", "pickup")
    for status in _ORDER_STATUS_VALUES
)


def can_set_order_status(user, fulfillment_type: str, status: str) -> bool:
    if can_edit(user, "orders"):
        return True
    return user.has_perm(f"accounts.set_order_{_order_party(fulfillment_type)}_status_{status}")


def grant(user, *codenames: str) -> None:
    group, _created = Group.objects.get_or_create(name=f"test-{user.pk}")
    perms = list(
        Permission.objects.filter(
            content_type__app_label="accounts",
            content_type__model="sectionaccess",
            codename__in=codenames,
        )
    )
    found = {perm.codename for perm in perms}
    missing = [code for code in codenames if code not in found]
    if missing:
        raise RuntimeError(f"Unknown section permissions: {missing}")
    group.permissions.add(*perms)
    user.groups.add(group)


def SectionPermission(section: str, also_view: tuple[str, ...] = ()):
    class _SectionPermission(BasePermission):
        def has_permission(self, request, view):
            if request.method in SAFE_METHODS:
                if can_view(request.user, section):
                    return True
                return any(can_view(request.user, extra) for extra in also_view)
            return can_edit(request.user, section)

    _SectionPermission.__name__ = f"SectionPermission_{section}"
    return _SectionPermission


def HasPerm(codename: str):
    class _HasPerm(BasePermission):
        def has_permission(self, request, view):
            return bool(request.user.is_authenticated and request.user.has_perm(f"accounts.{codename}"))

    _HasPerm.__name__ = f"HasPerm_{codename}"
    return _HasPerm


def CanView(*sections: str):
    class _CanView(BasePermission):
        def has_permission(self, request, view):
            return any(can_view(request.user, section) for section in sections)

    _CanView.__name__ = "CanView_" + "_".join(sections)
    return _CanView


class FinishedProductionAccess(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return can_view(request.user, "finished")
        return can_change_finished(request.user, None)


def EditSection(section: str):
    class _EditSection(BasePermission):
        def has_permission(self, request, view):
            return can_edit(request.user, section)

    _EditSection.__name__ = f"EditSection_{section}"
    return _EditSection
