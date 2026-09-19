from crm.models import CrmOrder
from crm.website import filling_for_website_order

updated = 0
skipped = 0
qs = (
    CrmOrder.objects.filter(website_order__isnull=False)
    .select_related("website_order")
    .prefetch_related("website_order__items__options")
    .order_by("id")
)
for crm_order in qs:
    new_filling = filling_for_website_order(crm_order.website_order)
    if new_filling is None or new_filling == crm_order.filling:
        skipped += 1
        continue
    print(
        f"#{crm_order.id} site {crm_order.website_order.number}: "
        f"{crm_order.filling!r} -> {new_filling!r}"
    )
    crm_order.filling = new_filling
    crm_order.save(update_fields=["filling", "updated_at"])
    updated += 1

print(f"updated={updated} skipped={skipped} total={updated + skipped}")
