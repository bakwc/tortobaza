from modeltranslation.translator import TranslationOptions, translator

from catalog.models import Category, Option, OptionGroup, Product, ProductImage


class CategoryTranslationOptions(TranslationOptions):
    fields = (
        "name",
        "page_slug",
        "page_heading",
        "page_description",
        "seo_title",
        "seo_description",
    )


class ProductTranslationOptions(TranslationOptions):
    fields = ("name", "description")


class OptionGroupTranslationOptions(TranslationOptions):
    fields = ("name",)


class OptionTranslationOptions(TranslationOptions):
    fields = ("name",)


class ProductImageTranslationOptions(TranslationOptions):
    fields = ("alt",)


translator.register(Category, CategoryTranslationOptions)
translator.register(Product, ProductTranslationOptions)
translator.register(OptionGroup, OptionGroupTranslationOptions)
translator.register(Option, OptionTranslationOptions)
translator.register(ProductImage, ProductImageTranslationOptions)
