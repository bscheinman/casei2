from ncaacards.logic import get_team_from_identifier
from ncaacards.models import NcaaGame, GameType
from trading.models import Order
from django import forms
from decimal import *


class TradeForm(forms.Form):
    team_identifier = forms.CharField(max_length=10)
    side = forms.ChoiceField(choices=[('buy', 'Buy'), ('sell', 'Sell')])
    price = forms.CharField(max_length=10)
    quantity = forms.CharField(max_length=10)
    cancel_on_game = forms.BooleanField(required=False, initial=True)

    def clean_cancel_on_game(self):
        if self['cancel_on_game'].html_name in self.data:
            return self.cleaned_data['cancel_on_game']
        else:
            return self.fields['cancel_on_game'].initial

    def clean(self):
        super(TradeForm, self).clean()
        cleaned_data = self.cleaned_data

        side = cleaned_data.get('side', '')
        price = cleaned_data.get('price', '')
        quantity = cleaned_data.get('quantity', '')
        cancel_on_game = cleaned_data.get('cancel_on_game', True)

        if not side in ['buy', 'sell']:
            self._errors['side'] = self.error_class(['Invalid side type %s' % side])

        if price:
            try:
                p = Decimal(price)
                cleaned_data['price'] = p
            except:
                self._errors['price'] = self.error_class(['%s is not a valid price' % price])
                del cleaned_data['price']
        else:
            self._errors['price'] = self.error_class(['You must enter a price'])

        if quantity:
            try:
                q = int(quantity)
            except:
                self._errors['quantity'] = self.error_class(['You must enter a valid integer quantity'])
                del cleaned_data['quantity']
            else:
                if q <= 0:
                    self._errors['quantity'] = self.error_class(['Trade quantity must be greater than zero'])
                    del cleaned_data['quantity']
                else:
                    cleaned_data['quantity'] = q
        else:
            self._errors['quantity'] = self.error_class(['You must enter a quantity'])

        return cleaned_data


class ChangeOrderForm(forms.Form):
    order_id = forms.CharField(max_length=32)
    quantity = forms.CharField(max_length=10, required=False)
    price = forms.CharField(max_length=10, required=False)
    cancel_on_game = forms.BooleanField(required=False)

    def clean(self):
        super(ChangeOrderForm, self).clean()
        cleaned_data = self.cleaned_data

        order_id = cleaned_data.get('order_id', '')
        quantity = cleaned_data.get('quantity', '')
        price = cleaned_data.get('price', '')
        cancel_on_game = cleaned_data.get('cancel_on_game', False)

        if order_id:
            try:
                order = Order.orders.get(order_id=order_id)
            except Order.DoesNotExist:
                self._errors['order_id'] = self.error_class(['No order exists with the ID %s' % order_id])
                del cleaned_data['order_id']
        else:
            self._errors['order_id'] = self.error_class(['You must provide an order ID'])
            
        if quantity:
            try:
                q = int(quantity)
            except ValueError:
                self._errors['quantity'] = self.error_class(['%s is not a valid quantity' % quantity])
                del cleaned_data['quantity']
            else:
                if q <= 0:
                    self._errors['quantity'] = self.error_class(['Quantity must be greater than zero'])
                    del cleaned_data['quantity']
                else:
                    cleaned_data['quantity'] = q

        if price:
            try:
                p = Decimal(price)
            except ValueError:
                self._errors['price'] = self.error_class(['%s is not a valid price' % price])
                del cleaned_data['price']
            else:
                cleaned_data['price'] = p

        return cleaned_data



class CreateGameForm(forms.Form):
    type_choices = []
    for gtype in GameType.objects.all():
        type_choices.append((gtype, gtype))

    game_name = forms.CharField(max_length=50)
    game_type = forms.ChoiceField(choices=type_choices)
    position_limit = forms.CharField(max_length=10, required=False)
    points_limit = forms.CharField(max_length=10, required=False)
    game_password = forms.CharField(widget=forms.PasswordInput, required=False)
    entry_name = forms.CharField(max_length=30)
    support_cards = forms.BooleanField(required=False)
    support_stocks = forms.BooleanField(required=False)

    def clean(self):
        super(CreateGameForm, self).clean()
        cleaned_data = self.cleaned_data

        game_name = cleaned_data.get('game_name', '')
        game_type_str = cleaned_data.get('game_type', '')
        position_limit_str = cleaned_data.get('position_limit', '')
        points_limit_str = cleaned_data.get('points_limit', '')
        game_password = cleaned_data.get('game_password', '')
        entry_name = cleaned_data.get('entry_name', '')
        support_cards = cleaned_data.get('support_cards', False)
        support_stocks = cleaned_data.get('support_stocks', False)

        if game_name:
            try:
                g = NcaaGame.objects.get(name=game_name)
            except NcaaGame.DoesNotExist:
                pass
            else:
                self._errors['game_name'] = self.error_class(['A game with already exists with the name %s' % game_name])
                del cleaned_data['game_name']
        else:
            self._errors['game_name'] = self.error_class(['You must specify a game name'])

        if game_type_str:
            try:
                game_type = GameType.objects.get(name=game_type_str)
            except GameType.DoesNotExist:
                self._errors['game_type'] = self.error_class(['%s is not a valid game type' % game_type_str])
                del cleaned_data['game_type']
            else:
                cleaned_data['game_type'] = game_type
        else:
            self._errors['game_type'] = self.error_class(['You must specify a game type'])

        if position_limit_str:
            try:
                position_limit = int(position_limit_str)
            except ValueError:
                self._errors['position_limit'] = self.error_class(['You must enter a valid position limit'])
                del cleaned_data['position_limit']
            else:
                if position_limit < 0:
                    self._errors['position_limit'] = self.error_class(['You cannot have a negative position limit'])
                    del cleaned_data['position_limit']
                elif position_limit > 0:
                    cleaned_data['position_limit'] = position_limit

        if points_limit_str:
            try:
                points_limit = int(points_limit_str)
            except ValueError:
                self._errors['points_limit'] = self.error_class(['You must enter a valid points limit'])
                del cleaned_data['points_limit']
            else:
                if support_stocks:
                    if points_limit < 0:
                        self._errors['points_limit'] = self.error_class(['You cannot have a negative points limit'])
                        del cleaned_data['points_limit']
                    elif points_limit > 0:
                        cleaned_data['points_limit'] = points_limit
        

        if not support_cards and not support_stocks:
            self._errors['support_cards'] = self.error_class(['You must select at least one trading type'])

        if not entry_name:
            self._errors['entry_name'] = self.error_class(['You must provide a name for your entry'])

        return cleaned_data
