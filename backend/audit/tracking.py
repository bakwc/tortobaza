from django.contrib.auth.models import User
from django.db.models import Model

from accounts.models import UserProfile
from attendance.models import AttendanceEvent
from catalog.models import Category, CategoryLanding, Option, OptionGroup, Product, ProductImage, ProductOptionGroup
from crm.models import CrmSettings, FinancialAccount, FinancialTransaction, FinancialTransactionRule
from inventory.models import (
    FinishedGood,
    FinishedProduction,
    InventoryCount,
    Production,
    Supplier,
    Supply,
    SupplyReceipt,
    WriteOff,
    WriteOffReason,
)
from menu.models import (
    Ingredient,
    IngredientCategory,
    ModifierGroup,
    SemiProduct,
    SemiProductImage,
    TechCard,
    TechCardCategory,
    TechCardImage,
)
from orders.models import LibertyPayment, Order, PayPalPayment, PickupLocation, PromoCode
from rsge.models import Invoice, Waybill

ROOTS = {
    User,
    UserProfile,
    AttendanceEvent,
    Category,
    CategoryLanding,
    OptionGroup,
    Option,
    Product,
    ProductImage,
    ProductOptionGroup,
    CrmSettings,
    FinancialAccount,
    FinancialTransaction,
    FinancialTransactionRule,
    Supplier,
    Supply,
    SupplyReceipt,
    Production,
    FinishedGood,
    FinishedProduction,
    WriteOffReason,
    WriteOff,
    InventoryCount,
    IngredientCategory,
    Ingredient,
    SemiProduct,
    SemiProductImage,
    ModifierGroup,
    TechCardCategory,
    TechCard,
    TechCardImage,
    PromoCode,
    PickupLocation,
    Order,
    LibertyPayment,
    PayPalPayment,
    Waybill,
    Invoice,
}

CHILDREN: dict[type[Model], tuple[str, ...]] = {
    OptionGroup: ("options",),
    Product: ("images", "product_option_groups"),
    FinancialTransactionRule: ("conditions",),
    Supply: ("lines", "receipts"),
    FinishedGood: ("modifiers",),
    FinishedProduction: ("lines",),
    WriteOff: ("lines",),
    InventoryCount: ("lines",),
    SemiProduct: ("lines", "images"),
    ModifierGroup: ("modifiers",),
    TechCard: ("sections", "lines", "modifier_groups", "modifier_lines", "images"),
    Order: ("items",),
    Waybill: ("goods",),
    Invoice: ("lines",),
}


def is_tracked(model: type[Model]) -> bool:
    return model._meta.concrete_model in ROOTS


def child_relations(model: type[Model]) -> tuple[str, ...]:
    return CHILDREN.get(model._meta.concrete_model, ())
