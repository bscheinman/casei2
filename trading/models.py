from __future__ import unicode_literals

from cix.fields import UUIDField
from decimal import Decimal
from django.contrib import admin
from django.core.cache import cache
from django.db import connection, models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver


class Market(models.Model):
    name = models.CharField(max_length=20, unique=True)
    game = models.ForeignKey('ncaacards.NcaaGame', blank=True, null=True)

    def __str__(self):
        return self.name


class Security(models.Model):
    market = models.ForeignKey(Market, related_name='securities')
    name = models.CharField(max_length=6)
    team = models.ForeignKey('ncaacards.GameTeam', blank=True, null=True)

    class Meta:
       unique_together = ('market', 'name')

    def __str__(self):
        return self.name

    def get_top_bids(self, count=5, entry=None):
    	bid_query = Q(is_active=True, quantity_remaining__gt=0, is_buy=True)
    	if entry:
    		bid_query = bid_query & Q(entry__id=entry.id)
        return self.orders.filter(bid_query).order_by('-price', 'last_modified')[:count].select_related('entry')

    def get_top_asks(self, count=5, entry=None):
    	ask_query = Q(is_active=True, quantity_remaining__gt=0, is_buy=False)
    	if entry:
    		ask_query = ask_query & Q(entry__id=entry.id)
        return self.orders.filter(ask_query).order_by('price', 'last_modified')[:count].select_related('entry')

    def get_bid(self):
        return self.get_bid_order().price

    def get_bid_order(self, entry=None):
        cache_key = 'bid_%s%s' % (self.id, ('|entry=%s' % entry.id) if entry else '')
        bid = cache.get(cache_key)
        if bid is None:
            bids = self.get_top_bids(1, entry)
            bid = bids[0] if bids else Order(price=0.0, quantity_remaining=0, is_active=False)
            cache.set(cache_key, bid, None)
        return bid

    def get_bidask_size_impl(self, is_buy):
        cursor = connection.cursor()
        query = """ SELECT SUM(quantity_remaining) AS total_qty
            FROM trading_order
            WHERE is_active = true AND is_buy = %s AND quantity_remaining > 0 AND security_id = %s
            GROUP BY price
            ORDER BY price %s
            LIMIT 1; """ % ('true' if is_buy else 'false', self.id, 'DESC' if is_buy else 'ASC')
        cursor.execute(query)
        row = cursor.fetchone()
        return row[0] if row else 0

    def get_bid_size(self):
        cache_key = 'bid_size_%s' % self.id
        bid_size = cache.get(cache_key)
        if bid_size is None:
            bid_size = self.get_bidask_size_impl(True)
            cache.set(cache_key, bid_size, None)
        return bid_size
    
    def get_ask_size(self):
        cache_key = 'ask_size_%s' % self.id
        ask_size = cache.get(cache_key)
        if ask_size is None:
            ask_size = self.get_bidask_size_impl(False)
            cache.set(cache_key, ask_size, None)
        return ask_size

    def get_ask(self):
        return self.get_ask_order().price

    def get_ask_order(self, entry=None):
        cache_key = 'ask_%s%s' % (self.id, ('|entry=%s' % entry.id) if entry else '')
        ask = cache.get(cache_key)
        if ask is None:
            asks = self.get_top_asks(1, entry)
            ask = asks[0] if asks else Order(price=0.0, quantity_remaining=0, is_active=False)
            cache.set(cache_key, ask, None)
        return ask

    def get_last(self):
        cache_key = 'last_%s' % self.id
        last = cache.get(cache_key)
        if last is None:
            execs = self.executions.order_by('-time')
            last = execs[0].price if execs else Decimal('0.0')
            cache.set(cache_key, last, None)
        return last

    def get_bbo(self):
        return (self.get_top_bids(5), self.get_top_asks(5))

    def get_bbo_table(self, depth=5):
        bids, asks = self.get_top_bids(depth), self.get_top_asks(depth)
        table = []
        for i in range(depth):
            bid = bids[i] if len(bids) > i else None
            ask = asks[i] if len(asks) > i else None
            if not bid and not ask:
                break
            table.append((bid, ask))
        return table


class OpenOrderManager(models.Manager):
    def get_queryset(self):
        return super(OpenOrderManager, self).get_queryset().filter(quantity_remaining__gt=0, is_active=True)

class Order(models.Model):
    order_id = UUIDField(auto=True, primary_key=True)
    placer = models.CharField(max_length=30) # This should be populated by the using application and is just for that application's use
    entry = models.ForeignKey('ncaacards.UserEntry', blank=True, null=True)
    security = models.ForeignKey(Security, related_name='orders')
    placed_time = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now_add=True)
    quantity = models.IntegerField()
    quantity_remaining = models.IntegerField()
    price = models.DecimalField(decimal_places=2, max_digits=10)
    is_buy = models.BooleanField()
    is_active = models.BooleanField(default=True)
    cancel_on_game = models.BooleanField(default=False)

    orders = models.Manager()
    open_orders = OpenOrderManager()

    def __str__(self):
        return self.order_id

    def side_name(self):
        return 'Buy' if self.is_buy else 'Sell'


class Execution(models.Model):
    security = models.ForeignKey(Security, related_name='executions', editable=False)
    execution_id = UUIDField(auto=True, primary_key=True, editable=False)
    buy_order = models.ForeignKey(Order, related_name='buy_executions', editable=False)
    sell_order = models.ForeignKey(Order, related_name='sell_executions', editable=False)
    quantity = models.IntegerField(editable=False)
    price = models.DecimalField(decimal_places=2, max_digits=10, editable=False)
    time = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return '%s   %s x %s @ %s' % (self.time.strftime('%a %m/%d %H:%M'), self.security.name, self.quantity, self.price)


admin.site.register(Market)
admin.site.register(Security)
admin.site.register(Order)
admin.site.register(Execution)


def process_order(order):
    def execute_orders(existing_order):
        exec_quantity = min([order.quantity_remaining, existing_order.quantity_remaining])

        if order.is_buy:
            buy_order = order
            sell_order = existing_order
        else:
            buy_order = existing_order
            sell_order = order

        if buy_order.placer == sell_order.placer:
            buy_order.quantity_remaining -= exec_quantity
            buy_order.save()
            sell_order.quantity_remaining -= exec_quantity
            sell_order.save()
        else:
            execution = Execution.objects.create(security=order.security, buy_order=buy_order,\
                sell_order=sell_order, quantity=exec_quantity, price=existing_order.price)

    if order.is_buy:
        comparer = lambda x: x.price <= order.price
        order_generator = lambda: order.security.get_top_asks()
    else:
        comparer = lambda x: x.price >= order.price
        order_generator = lambda: order.security.get_top_bids()

    while True:
        matching_orders = order_generator()
        if not matching_orders:
            return
        for matching_order in matching_orders:
            if not comparer(matching_order):
                return
            execute_orders(matching_order)
            if order.quantity_remaining <= 0:
                return


@receiver(post_save, sender=Order, weak=False)
def on_new_order(sender, instance, created, **kwargs):
    if created:
        process_order(instance)
    # In the future we can try to be a little smarter about which cache values to reset, but
    # for now even this will be a huge improvement since the ratio of orders to page views
    # right now is very low
    sec_id = instance.security.id
    entry_id = instance.entry.id
    for tag in ('bid', 'ask', 'bid_size', 'ask_size'):
    	cache_key = '%s_%s' % (tag, sec_id)
    	cache.delete(cache_key)
    	cache.delete(cache_key + '|entry=%s' % entry_id)


@receiver(post_save, sender=Execution, weak=False)
def record_execution(sender, instance, created, **kwargs):
    if created:
        instance.buy_order.quantity_remaining -= instance.quantity
        instance.buy_order.save()
        instance.sell_order.quantity_remaining -= instance.quantity
        instance.sell_order.save()
    cache.delete('last_%s' % instance.security.id)
