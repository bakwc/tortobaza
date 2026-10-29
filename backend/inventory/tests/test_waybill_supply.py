from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from inventory.models import StockMovement, Supplier, Supply, WaybillIngredientAlias
from inventory.waybill_supply import (
    WAYBILL_MATCH_MODEL,
    WaybillGoodMatchModel,
    WaybillMatchModel,
    WaybillSuggestionModel,
)
from menu.models import UNIT_GRAM, UNIT_MILLILITER, Ingredient
from rsge.models import Waybill, WaybillGood

TB = ZoneInfo("Asia/Tbilisi")


def make_waybill(
    rs_id: int,
    number: str,
    seller_tin: str,
    seller_name: str,
    seller_name_ru: str,
    delivery: datetime | None,
) -> Waybill:
    created = datetime(2026, 10, 1, 12, 0, tzinfo=TB)
    return Waybill.objects.create(
        rs_id=rs_id,
        waybill_number=number,
        type=3,
        status=1,
        create_date=created,
        activate_date=created,
        begin_date=created,
        delivery_date=delivery,
        buyer_tin="1",
        buyer_name="Buyer",
        seller_tin=seller_tin,
        seller_name=seller_name,
        seller_name_ru=seller_name_ru,
        transport_coast=Decimal("0"),
        full_amount=Decimal("45.50"),
        s_user_id=1,
        is_confirmed=1,
        is_corrected=0,
        seller_st=0,
        is_med=0,
    )


def make_good(
    waybill: Waybill,
    rs_id: int,
    name: str,
    name_ru: str,
    quantity: str,
    amount: str,
    bar_code: str,
    unit_txt: str,
) -> WaybillGood:
    return WaybillGood.objects.create(
        waybill=waybill,
        rs_id=rs_id,
        name=name,
        name_ru=name_ru,
        unit_id=1,
        unit_txt=unit_txt,
        quantity=Decimal(quantity),
        price=Decimal(amount),
        amount=Decimal(amount),
        bar_code=bar_code,
        vat_type=0,
        status=1,
        quantity_f=Decimal(quantity),
    )


def supply_line(good: WaybillGood, ingredient: Ingredient | None, quantity: str | None, skipped: bool) -> dict:
    return {
        "good_id": good.pk,
        "ingredient": None if ingredient is None else ingredient.pk,
        "quantity": quantity,
        "skipped": skipped,
    }


def suggestion(ingredient_id: int | None, factor: str, unit: str) -> WaybillSuggestionModel:
    return WaybillSuggestionModel(ingredient_id=ingredient_id, factor=factor, unit=unit)


class WaybillSupplyApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user("chef", password="x")
        self.admin = User.objects.create_user("boss", password="x")
        UserProfile.objects.create(user=self.admin, is_finance_admin=True)
        self.flour = Ingredient.objects.create(name="Мука", unit=UNIT_GRAM)
        Ingredient.objects.create(name="Скрытая мука", unit=UNIT_GRAM, is_active=False)
        self.milk = Ingredient.objects.create(name="Молоко", unit=UNIT_MILLILITER)
        self.waybill = make_waybill(1, "101", "445712532", "Milk Co", "Молочный", datetime(2026, 10, 14, 22, 0, tzinfo=TB))
        self.milk_good = make_good(self.waybill, 10, "რძე 1ლ", "Молоко 1 л", "10", "45.50", "", "ც")

    def draft(self, waybill: Waybill):
        return self.client.post(f"/api/rsge/waybills/{waybill.pk}/supply-draft/")

    def create(self, waybill: Waybill, lines: list[dict]):
        return self.client.post(f"/api/rsge/waybills/{waybill.pk}/supply/", {"lines": lines}, format="json")

    def test_requires_finance_admin(self):
        self.client.force_authenticate(self.staff)
        response = self.draft(self.waybill)
        self.assertEqual(response.status_code, 403)

    @patch("inventory.waybill_supply.OpenAI")
    def test_saved_alias_skips_the_model(self, openai_cls):
        WaybillIngredientAlias.objects.create(
            seller_tin=self.waybill.seller_tin,
            bar_code="",
            name=self.milk_good.name,
            unit_txt=self.milk_good.unit_txt,
            ingredient=self.milk,
            factor=Decimal("1000"),
            ignored=False,
        )
        self.client.force_authenticate(self.admin)
        response = self.draft(self.waybill)
        self.assertEqual(response.status_code, 200, response.content)
        openai_cls.assert_not_called()
        line = response.json()["lines"][0]
        self.assertEqual(line["alias"]["ingredient_id"], self.milk.pk)
        self.assertEqual(line["alias"]["factor"], "1000.000000")
        self.assertEqual(line["suggestions"], [])
        self.assertEqual(response.json()["date"], "2026-10-14")
        self.assertEqual(response.json()["supplier_name"], "Молочный")
        self.assertIsNone(response.json()["supplier"])

    @patch("inventory.waybill_supply.OpenAI")
    def test_unmatched_lines_are_sent_once(self, openai_cls):
        boxed = make_good(self.waybill, 11, "ყუთი", "Коробка", "1", "0", "999", "ც")
        WaybillIngredientAlias.objects.create(
            seller_tin=self.waybill.seller_tin,
            bar_code="",
            name=self.milk_good.name,
            unit_txt=self.milk_good.unit_txt,
            ingredient=self.milk,
            factor=Decimal("1000"),
            ignored=False,
        )
        openai_cls.return_value.responses.parse.return_value.output_parsed = WaybillMatchModel(
            lines=[
                WaybillGoodMatchModel(
                    good_id=boxed.pk,
                    suggestions=[suggestion(self.flour.pk, "1", "g")],
                )
            ]
        )
        self.client.force_authenticate(self.admin)
        response = self.draft(self.waybill)
        self.assertEqual(response.status_code, 200, response.content)
        openai_cls.return_value.responses.parse.assert_called_once()
        call = openai_cls.return_value.responses.parse.call_args.kwargs
        self.assertEqual(call["model"], WAYBILL_MATCH_MODEL)
        self.assertIs(call["text_format"], WaybillMatchModel)
        self.assertFalse(call["store"])
        text = call["input"][0]["content"][0]["text"]
        self.assertIn(str(boxed.pk), text)
        self.assertNotIn(self.milk_good.name, text)
        self.assertIn("Мука", text)
        self.assertNotIn("Скрытая мука", text)
        lines = response.json()["lines"]
        self.assertEqual(lines[0]["suggestions"], [])
        self.assertEqual(lines[1]["suggestions"], [{"ingredient_id": self.flour.pk, "factor": "1", "unit": "g"}])

    @patch("inventory.waybill_supply.OpenAI")
    def test_unknown_ingredient_id_fails(self, openai_cls):
        openai_cls.return_value.responses.parse.return_value.output_parsed = WaybillMatchModel(
            lines=[WaybillGoodMatchModel(good_id=self.milk_good.pk, suggestions=[suggestion(999999, "1", "g")])]
        )
        self.client.force_authenticate(self.admin)
        response = self.draft(self.waybill)
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("999999", str(response.json()))

    @patch("inventory.waybill_supply.OpenAI")
    def test_empty_model_output_fails(self, openai_cls):
        openai_cls.return_value.responses.parse.return_value.output_parsed = None
        self.client.force_authenticate(self.admin)
        response = self.draft(self.waybill)
        self.assertEqual(response.status_code, 400, response.content)

    def test_creates_supply_stock_supplier_and_alias(self):
        self.client.force_authenticate(self.admin)
        response = self.create(self.waybill, [supply_line(self.milk_good, self.milk, "10000", False)])
        self.assertEqual(response.status_code, 201, response.content)
        self.waybill.refresh_from_db()
        self.assertEqual(
            response.json()["waybill"],
            {
                "id": self.waybill.pk,
                "waybill_number": "101",
                "create_date": self.waybill.create_date.isoformat(),
                "full_amount": str(self.waybill.full_amount),
            },
        )
        supply = Supply.objects.get()
        self.assertEqual(supply.waybill_id, self.waybill.pk)
        self.assertEqual(supply.date.isoformat(), "2026-10-14")
        self.assertEqual(supply.comment, "101")
        self.assertIsNone(supply.financial_transaction_id)
        self.assertEqual(supply.created_by_id, self.admin.pk)
        self.assertEqual(list(supply.receipts.all()), [])
        line = supply.lines.get()
        self.assertEqual(line.ingredient_id, self.milk.pk)
        self.assertEqual(line.quantity, Decimal("10000.000"))
        self.assertEqual(line.total, Decimal("45.50"))
        movement = StockMovement.objects.get(kind=StockMovement.KIND_SUPPLY)
        self.assertEqual(movement.quantity, Decimal("10000.000"))
        self.assertEqual(movement.ingredient_id, self.milk.pk)
        supplier = Supplier.objects.get()
        self.assertEqual(supplier.name, "Молочный")
        self.assertEqual(supplier.tin, "445712532")
        self.assertEqual(supply.supplier_id, supplier.pk)
        alias = WaybillIngredientAlias.objects.get()
        self.assertEqual(alias.seller_tin, "445712532")
        self.assertEqual(alias.name, "რძე 1ლ")
        self.assertEqual(alias.unit_txt, "ც")
        self.assertEqual(alias.bar_code, "")
        self.assertEqual(alias.ingredient_id, self.milk.pk)
        self.assertEqual(alias.factor, Decimal("1000.000000"))
        self.assertFalse(alias.ignored)
        listed = self.client.get("/api/rsge/waybills/", {"month": "2026-10"})
        self.assertEqual(listed.json()[0]["supply_id"], supply.pk)
        self.assertEqual(listed.json()[0]["supply"]["id"], supply.pk)
        self.assertEqual(listed.json()[0]["supply"]["date"], "2026-10-14")
        self.assertEqual(listed.json()[0]["supply"]["total"], "45.50")

    @patch("inventory.waybill_supply.OpenAI")
    def test_second_waybill_with_the_same_name_is_prefilled(self, openai_cls):
        self.client.force_authenticate(self.admin)
        created = self.create(self.waybill, [supply_line(self.milk_good, self.milk, "10000", False)])
        self.assertEqual(created.status_code, 201, created.content)
        second = make_waybill(2, "102", "445712532", "Milk Co", "Молочный", None)
        make_good(second, 20, "რძე 1ლ", "Молоко 1 л", "2", "9", "", "ც")
        response = self.draft(second)
        self.assertEqual(response.status_code, 200, response.content)
        openai_cls.assert_not_called()
        self.assertEqual(response.json()["date"], "2026-10-01")
        self.assertEqual(response.json()["supplier"]["id"], Supplier.objects.get().pk)
        self.assertEqual(response.json()["lines"][0]["alias"]["ingredient_id"], self.milk.pk)
        self.assertEqual(response.json()["lines"][0]["alias"]["factor"], "1000.000000")

    @patch("inventory.waybill_supply.OpenAI")
    def test_barcode_alias_matches_across_names(self, openai_cls):
        coded = make_good(self.waybill, 12, "რძე", "Молоко", "1", "4", "860000", "ც")
        self.client.force_authenticate(self.admin)
        created = self.create(
            self.waybill,
            [
                supply_line(self.milk_good, self.milk, "10000", False),
                supply_line(coded, self.milk, "1000", False),
            ],
        )
        self.assertEqual(created.status_code, 201, created.content)
        second = make_waybill(3, "103", "445712532", "Milk Co", "", None)
        make_good(second, 30, "სხვა სახელი", "Другое", "4", "16", "860000", "კგ")
        response = self.draft(second)
        self.assertEqual(response.status_code, 200, response.content)
        openai_cls.assert_not_called()
        self.assertEqual(response.json()["lines"][0]["alias"]["ingredient_id"], self.milk.pk)
        self.assertEqual(response.json()["supplier_name"], "Milk Co")

    @patch("inventory.waybill_supply.OpenAI")
    def test_skipped_line_is_remembered(self, openai_cls):
        box = make_good(self.waybill, 13, "ყუთი", "Коробка", "1", "0", "", "ც")
        self.client.force_authenticate(self.admin)
        created = self.create(
            self.waybill,
            [
                supply_line(self.milk_good, self.milk, "10000", False),
                supply_line(box, None, None, True),
            ],
        )
        self.assertEqual(created.status_code, 201, created.content)
        alias = WaybillIngredientAlias.objects.get(name="ყუთი")
        self.assertTrue(alias.ignored)
        self.assertIsNone(alias.ingredient_id)
        self.assertIsNone(alias.factor)
        second = make_waybill(4, "104", "445712532", "Milk Co", "Молочный", None)
        make_good(second, 40, "რძე 1ლ", "Молоко 1 л", "1", "4", "", "ც")
        make_good(second, 41, "ყუთი", "Коробка", "2", "0", "", "ც")
        response = self.draft(second)
        self.assertEqual(response.status_code, 200, response.content)
        openai_cls.assert_not_called()
        self.assertFalse(response.json()["lines"][0]["alias"]["ignored"])
        self.assertTrue(response.json()["lines"][1]["alias"]["ignored"])

    def test_second_supply_is_rejected(self):
        self.client.force_authenticate(self.admin)
        first = self.create(self.waybill, [supply_line(self.milk_good, self.milk, "10000", False)])
        self.assertEqual(first.status_code, 201, first.content)
        second = self.create(self.waybill, [supply_line(self.milk_good, self.flour, "10", False)])
        self.assertEqual(second.status_code, 400, second.content)
        self.assertEqual(Supply.objects.count(), 1)
        self.assertEqual(Supply.objects.get().lines.get().ingredient_id, self.milk.pk)

    def test_all_skipped_lines_are_rejected(self):
        self.client.force_authenticate(self.admin)
        response = self.create(self.waybill, [supply_line(self.milk_good, None, None, True)])
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(Supply.objects.exists())
        self.assertFalse(WaybillIngredientAlias.objects.exists())

    def test_zero_waybill_quantity_is_rejected(self):
        empty = make_good(self.waybill, 14, "ნული", "Ноль", "0", "0", "", "ც")
        self.client.force_authenticate(self.admin)
        response = self.create(
            self.waybill,
            [
                supply_line(self.milk_good, self.milk, "10000", False),
                supply_line(empty, self.flour, "1", False),
            ],
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(Supply.objects.exists())

    def test_existing_supplier_name_receives_tin(self):
        supplier = Supplier.objects.create(name="Молочный")
        self.client.force_authenticate(self.admin)
        response = self.create(self.waybill, [supply_line(self.milk_good, self.milk, "10000", False)])
        self.assertEqual(response.status_code, 201, response.content)
        supplier.refresh_from_db()
        self.assertEqual(supplier.tin, "445712532")
        self.assertEqual(Supply.objects.get().supplier_id, supplier.pk)
        self.assertEqual(Supplier.objects.count(), 1)

    def test_supplier_is_matched_by_tin(self):
        supplier = Supplier.objects.create(name="Другой", tin="445712532")
        self.client.force_authenticate(self.admin)
        response = self.create(self.waybill, [supply_line(self.milk_good, self.milk, "10000", False)])
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Supply.objects.get().supplier_id, supplier.pk)
        self.assertEqual(Supplier.objects.count(), 1)

    def test_supplier_name_owned_by_another_tin_fails(self):
        Supplier.objects.create(name="Молочный", tin="999")
        self.client.force_authenticate(self.admin)
        response = self.create(self.waybill, [supply_line(self.milk_good, self.milk, "10000", False)])
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(Supply.objects.exists())
        self.assertEqual(Supplier.objects.get().tin, "999")
