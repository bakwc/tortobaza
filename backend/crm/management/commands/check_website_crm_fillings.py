from collections import Counter

from django.core.management.base import BaseCommand

from catalog.models import OptionGroup
from crm.models import CrmOrder
from crm.website import _FILLING_GROUPS, _item_label, _option_names
from orders.models import OrderItemOption


def _live_filling(order) -> str:
    filling_parts = _option_names(order, _FILLING_GROUPS)
    if filling_parts:
        return ", ".join(filling_parts)
    return ", ".join(_item_label(item) for item in order.items.all())


class Command(BaseCommand):
    help = "Check website CRM filling matching for catalog groups and existing orders"

    def handle(self, *args, **options):
        self.stdout.write(
            "sync filling group names: " + ", ".join(sorted(_FILLING_GROUPS))
        )
        self.stdout.write("")
        self.stdout.write("=== catalog option groups ===")
        for group in OptionGroup.objects.order_by("slug"):
            self.stdout.write(f"slug={group.slug}")
            for lang, value in (
                ("en", group.name_en),
                ("ka", group.name_ka),
                ("ru", group.name_ru),
            ):
                matched = bool(value) and value.casefold() in _FILLING_GROUPS
                self.stdout.write(
                    f"  {lang}={value!r} filling_match={matched}"
                )
        self.stdout.write("")
        self.stdout.write("=== group_name snapshots on website CRM orders ===")
        group_names = OrderItemOption.objects.filter(
            order_item__order__crm_order__isnull=False
        ).values_list("group_name", flat=True)
        counts = Counter(group_names)
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
            matched = name.casefold() in _FILLING_GROUPS
            self.stdout.write(
                f"  {name!r} count={count} filling_match={matched}"
            )
        self.stdout.write("")
        self.stdout.write("=== existing website CRM orders vs live sync ===")
        qs = (
            CrmOrder.objects.filter(website_order__isnull=False)
            .select_related("website_order")
            .prefetch_related("website_order__items__options")
            .order_by("id")
        )
        mismatch = 0
        total = 0
        for crm_order in qs:
            total += 1
            expected = _live_filling(crm_order.website_order)
            if expected == crm_order.filling:
                continue
            mismatch += 1
            self.stdout.write(
                f"#{crm_order.id} site {crm_order.website_order.number}: "
                f"stored={crm_order.filling!r} live_sync={expected!r}"
            )
        self.stdout.write(f"mismatch={mismatch} total={total}")
