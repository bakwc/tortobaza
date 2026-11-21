from pathlib import Path

from django.core.files.base import ContentFile
from django.db import models, transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from menu.models import (
    SemiProduct,
    SemiProductImage,
    SemiProductLine,
    TechCard,
    TechCardImage,
    TechCardLine,
    TechCardModifierGroup,
    TechCardModifierLine,
    TechCardSection,
)


class CloneNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)


def ensure_unique_name(model: type[models.Model], name: str) -> None:
    if model.objects.filter(name=name).exists():
        raise ValidationError({"name": ["This name is already used."]})


def duplicate_file(source_field, dest_field) -> None:
    with source_field.open("rb") as handle:
        payload = handle.read()
    dest_field.save(Path(source_field.name).name, ContentFile(payload), save=False)


@transaction.atomic
def clone_tech_card(source: TechCard, name: str) -> TechCard:
    ensure_unique_name(TechCard, name)
    clone = TechCard.objects.create(
        name=name,
        category=source.category,
        kind=source.kind,
        basis_weight_kg=source.basis_weight_kg,
        basis_quantity=source.basis_quantity,
        sale_price=source.sale_price,
        method=source.method,
        shelf_life_seconds=source.shelf_life_seconds,
        storage_temperature=source.storage_temperature,
        is_active=source.is_active,
    )
    sections = {}
    for section in source.sections.all():
        sections[section.pk] = TechCardSection.objects.create(
            tech_card=clone,
            name=section.name,
            method=section.method,
            position=section.position,
        )
    for line in source.lines.all():
        TechCardLine.objects.create(
            tech_card=clone,
            section=None if line.section_id is None else sections[line.section_id],
            ingredient=line.ingredient,
            semi_product=line.semi_product,
            quantity=line.quantity,
            quantity_unit=line.quantity_unit,
            loss_quantity=line.loss_quantity,
            nested_tech_card=line.nested_tech_card,
            nested_section=None if line.nested_section_id is None else sections[line.nested_section_id],
            position=line.position,
        )
    for link in source.modifier_groups.all():
        TechCardModifierGroup.objects.create(
            tech_card=clone,
            group=link.group,
            is_required=link.is_required,
            position=link.position,
        )
    for line in source.modifier_lines.all():
        TechCardModifierLine.objects.create(
            tech_card=clone,
            modifier=line.modifier,
            ingredient=line.ingredient,
            semi_product=line.semi_product,
            nested_tech_card=line.nested_tech_card,
            quantity=line.quantity,
            quantity_unit=line.quantity_unit,
            loss_quantity=line.loss_quantity,
            scales_by_weight=line.scales_by_weight,
            position=line.position,
        )
    for image in source.images.all():
        copy = TechCardImage(tech_card=clone, position=image.position)
        duplicate_file(image.image, copy.image)
        copy.save()
    return clone


@transaction.atomic
def clone_semi_product(source: SemiProduct, name: str) -> SemiProduct:
    ensure_unique_name(SemiProduct, name)
    clone = SemiProduct.objects.create(
        name=name,
        category=source.category,
        unit=source.unit,
        yield_quantity=source.yield_quantity,
        is_produced=source.is_produced,
        is_active=source.is_active,
        method=source.method,
    )
    for line in source.lines.all():
        SemiProductLine.objects.create(
            parent=clone,
            ingredient=line.ingredient,
            semi_product=line.semi_product,
            quantity=line.quantity,
            quantity_unit=line.quantity_unit,
            loss_quantity=line.loss_quantity,
            position=line.position,
        )
    for image in source.images.all():
        copy = SemiProductImage(semi_product=clone, position=image.position)
        duplicate_file(image.image, copy.image)
        copy.save()
    return clone
