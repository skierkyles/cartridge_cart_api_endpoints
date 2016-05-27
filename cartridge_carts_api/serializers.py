import os

from django.contrib.staticfiles.templatetags.staticfiles import static

from cartridge.shop.models import Cart, CartItem, ProductVariation
from rest_framework import serializers


class CartAddItemSerializer(serializers.Serializer):
    sku = serializers.CharField()
    quantity = serializers.IntegerField(min_value=-5000, max_value=5000)


class CartItemSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    variation = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ('id', 'sku', 'name', 'description', 'quantity', 'unit_price', 'total_price',
                  'image', 'variation', )

    def __get_by_sku(self, sku):
        return ProductVariation.objects.get(sku=sku)

    def get_image(self, obj):
        with_media = os.path.join('media', obj.image)

        return static(with_media)

    def get_variation(self, obj):
        p = self.__get_by_sku(obj.sku)

        options = {}
        for field in p.option_fields():
            name = getattr(p, field.name)
            if name is not None:
                options[field.verbose_name.lower()] = name

        return options

    def get_name(self, obj):
        p = self.__get_by_sku(obj.sku)

        return unicode(p.product)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True)

    class Meta:
        model = Cart
        fields = ('total_price', 'total_quantity', 'items', )
