from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from catalog.img_view import clear_image_cache
from catalog.models import ProductImage


@receiver(pre_save, sender=ProductImage)
def product_image_invalidate_old_file(sender, instance, **kwargs):
    if not instance.pk:
        return
    prev = ProductImage.objects.filter(pk=instance.pk).first()
    if prev is None:
        return
    if prev.image.name != instance.image.name:
        clear_image_cache(prev.image.name)


@receiver(post_delete, sender=ProductImage)
def product_image_invalidate_on_delete(sender, instance, **kwargs):
    clear_image_cache(instance.image.name)
