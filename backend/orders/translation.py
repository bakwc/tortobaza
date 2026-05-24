from modeltranslation.translator import TranslationOptions, translator

from orders.models import PickupLocation


class PickupLocationTranslationOptions(TranslationOptions):
    fields = ("name", "address")


translator.register(PickupLocation, PickupLocationTranslationOptions)
