from cartridge.shop.models import ProductVariation
from rest_framework import generics
from rest_framework.response import Response
from cartridge.shop.utils import recalculate_cart

from carts.serializers import CartSerializer, CartAddItemSerializer
from main.mixins import CheckCartMixin, SetSessionCookieMixin


def not_enough_stock_error(quantity):
    return Response({'notEnoughStock': True, 'quantityLeft': quantity}, status=400)


def no_sku_error():
    return Response({'error': 'No Variation of that SKU found'}, status=400)


class CartRetrieveView(CheckCartMixin, SetSessionCookieMixin, generics.RetrieveAPIView):
    """ View responsible for getting the proper cart object, and
    returning all items in the cart.
    """
    serializer_class = CartSerializer

    def get_object(self):
        return self.request.cart


class CartModifyView(CheckCartMixin, SetSessionCookieMixin, generics.CreateAPIView):
    serializer_class = CartAddItemSerializer

    def get_data(self, data):
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        sku = serializer.data.get('sku')
        quantity = serializer.data.get('quantity')

        return sku, quantity

    def get_variation(self, sku):
        return ProductVariation.objects.filter(sku__iexact=sku).first()


class CartAddView(CartModifyView):
    """ Accepts a sku and quantity.
    Adds quantity to the current number you may or
    may not have.
    Returns the updated state of the cart.
    """
    def create(self, request, *args, **kwargs):
        sku, quantity = self.get_data(request.data)
        variation = self.get_variation(sku)

        if variation is None:
            return no_sku_error()

        able_to_purchase = variation is not None and variation.has_stock(quantity)
        not_enough_stock = variation is not None and variation.has_stock(quantity) is False

        if able_to_purchase:
            request.cart.add_item(variation, quantity)
            recalculate_cart(request)

            return Response(CartSerializer(request.cart).data)
        elif not_enough_stock:
            quantity_available = variation.live_num_in_stock()
            return not_enough_stock_error(quantity_available)


class CartEditView(CartModifyView):
    """ Accepts a sku and quantity.
    Sets that variation to quantity in your cart.
    To remove a variation, set to 0.
    Returns the updated state of the cart.
    """
    def create(self, request, *args, **kwargs):
        sku, quantity = self.get_data(request.data)
        variation = self.get_variation(sku)

        if variation is None:
            return no_sku_error()

        kwargs = {"sku": variation.sku, "unit_price": variation.price()}
        in_cart = request.cart.items.filter(**kwargs).first()
        if in_cart is not None:
            if quantity <= 0:
                in_cart.delete()
            else:
                if variation.has_stock(quantity) is False:
                    quantity_available = variation.live_num_in_stock()
                    return not_enough_stock_error(quantity_available)

                in_cart.quantity = quantity
                in_cart.save()
        elif quantity > 0:
            request.cart.add_item(variation, quantity)
            recalculate_cart(request)

        able_to_purchase = variation is not None and variation.has_stock(quantity)
        not_enough_stock = variation is not None and variation.has_stock(quantity) is False

        if able_to_purchase:
            return Response(CartSerializer(request.cart).data)
        elif not_enough_stock:
            quantity_available = variation.live_num_in_stock()
            return not_enough_stock_error(quantity_available)
