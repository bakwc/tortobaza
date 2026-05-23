import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tortobaza.settings")
django.setup()

from catalog.models import (
    Category,
    OptionGroup,
    Option,
    Product,
    ProductOptionGroup,
)
from orders.models import PickupLocation


def main() -> None:
    cats = [
        ("Simple cake", "simple-cake", 0, Product.DELIVERY_SCHEDULE_SAME_DAY),
        ("Standard cake", "standard-cake", 1, Product.DELIVERY_SCHEDULE_NEXT_DAY),
        ("Desserts", "desserts", 2, Product.DELIVERY_SCHEDULE_SAME_DAY),
        ("Gifts", "gifts", 3, Product.DELIVERY_SCHEDULE_SAME_DAY),
    ]
    cat_objs: dict[str, Category] = {}
    for name, slug, pos, tier in cats:
        obj, _ = Category.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "position": pos,
                "is_active": True,
                "delivery_schedule_tier": tier,
            },
        )
        cat_objs[slug] = obj

    filling, _ = OptionGroup.objects.update_or_create(
        slug="filling",
        defaults={
            "name": "Filling",
            "selection_type": OptionGroup.SELECTION_SINGLE,
            "is_required_default": True,
        },
    )
    for name, delta, pos in [
        ("Raspberry", "0.00", 0),
        ("Strawberry", "30.00", 1),
        ("Mango", "30.00", 2),
        ("Pistachio", "60.00", 3),
    ]:
        Option.objects.update_or_create(
            group=filling, name=name, defaults={"price_delta": delta, "position": pos}
        )

    sponge, _ = OptionGroup.objects.update_or_create(
        slug="sponge",
        defaults={
            "name": "Sponge",
            "selection_type": OptionGroup.SELECTION_SINGLE,
            "is_required_default": True,
        },
    )
    for name, delta, pos in [
        ("Vanilla", "0.00", 0),
        ("Chocolate", "20.00", 1),
        ("Red velvet", "40.00", 2),
    ]:
        Option.objects.update_or_create(
            group=sponge, name=name, defaults={"price_delta": delta, "position": pos}
        )

    extras, _ = OptionGroup.objects.update_or_create(
        slug="extras",
        defaults={
            "name": "Extras",
            "selection_type": OptionGroup.SELECTION_MULTI,
            "is_required_default": False,
        },
    )
    for name, delta, pos in [
        ("Edible flowers", "50.00", 0),
        ("Gold leaf", "120.00", 1),
        ("Greeting card", "20.00", 2),
    ]:
        Option.objects.update_or_create(
            group=extras, name=name, defaults={"price_delta": delta, "position": pos}
        )

    products = [
        (
            "simple-cake",
            "Raspberry Dream",
            "raspberry-dream",
            "Light sponge with seasonal raspberries.",
            "180.00",
            None,
        ),
        (
            "simple-cake",
            "Vanilla Cloud",
            "vanilla-cloud",
            "Soft vanilla sponge, mascarpone cream.",
            "160.00",
            None,
        ),
        (
            "standard-cake",
            "Pistachio Honey",
            "pistachio-honey",
            "Rich pistachio sponge with honey cream.",
            "260.00",
            None,
        ),
        (
            "standard-cake",
            "Chocolate Velvet",
            "chocolate-velvet",
            "Three layers of dark chocolate velvet.",
            "240.00",
            Product.DELIVERY_SCHEDULE_PLUS_2,
        ),
        (
            "desserts",
            "Lemon Tart",
            "lemon-tart",
            "Crisp tart shell, silky lemon curd.",
            "60.00",
            None,
        ),
        (
            "desserts",
            "Tiramisu Cup",
            "tiramisu-cup",
            "Classic tiramisu in a cup.",
            "55.00",
            Product.DELIVERY_SCHEDULE_PLUS_3,
        ),
        (
            "gifts",
            "Box of Macarons",
            "box-of-macarons",
            "Twelve assorted macarons in a gift box.",
            "120.00",
            None,
        ),
    ]
    for cat_slug, name, slug, desc, price, tier in products:
        prod, _ = Product.objects.update_or_create(
            slug=slug,
            defaults={
                "category": cat_objs[cat_slug],
                "name": name,
                "description": desc,
                "delivery_schedule_tier": tier,
                "is_active": True,
            },
        )
        ProductOptionGroup.objects.update_or_create(
            product=prod, option_group=filling, defaults={"position": 0}
        )
        ProductOptionGroup.objects.update_or_create(
            product=prod, option_group=sponge, defaults={"position": 1}
        )
        ProductOptionGroup.objects.update_or_create(
            product=prod, option_group=extras, defaults={"position": 2}
        )

    PickupLocation.objects.update_or_create(
        name="Tortobaza — Main shop",
        defaults={
            "address": "Sheikh Zayed Road, Dubai",
            "is_active": True,
        },
    )
    PickupLocation.objects.update_or_create(
        name="Tortobaza — Marina",
        defaults={
            "address": "Marina Walk, Dubai",
            "is_active": True,
        },
    )

    print("seed done")


if __name__ == "__main__":
    main()
