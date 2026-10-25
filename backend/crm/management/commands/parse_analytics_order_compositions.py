from django.core.management.base import BaseCommand

from crm.analytics_composition import sync_analytics_composition
from crm.models import AnalyticsOrderComposition, CrmOrder


class Command(BaseCommand):
    help = "Parse CRM orders into analytics order compositions"

    def handle(self, *args, **options):
        orders = (
            CrmOrder.objects.filter(deleted=False)
            .select_related("website_order")
            .prefetch_related("website_order__items__options__option")
            .order_by("id")
        )
        rules = 0
        llm = 0
        skipped = 0
        for order in orders:
            composition, changed = sync_analytics_composition(order)
            if not changed:
                skipped += 1
            elif composition.parser == AnalyticsOrderComposition.PARSER_RULES:
                rules += 1
            else:
                llm += 1
        self.stdout.write(f"rules={rules} llm={llm} skipped={skipped}")
