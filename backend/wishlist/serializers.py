from rest_framework import serializers

from wishlist.models import WishlistItem


class WishlistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WishlistItem
        fields = ["id", "title", "purpose", "priority", "cost"]
