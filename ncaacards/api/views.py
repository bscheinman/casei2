from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from ncaacards.models import *
from trading.models import Execution, Order
import json

def needs_entry(fn):
    def wrapper(request):
        apid_str = request.POST.get('apid', None)
        if not apid_str:
            result = { 'error': 'missing apid' }
        else:
            try:
                apid = uuid.UUID(apid_str)
                entry = UserEntry.objects.get(apid=apid)
            except:
                result = { 'error': 'invalid apid' }
            else:
                result = fn(request, entry)

        return HttpResponse(json.dumps(result))

    return wrapper

@csrf_exempt
@needs_entry
def make_market(request, entry):
    return { 'entry_name': entry.entry_name }

@csrf_exempt
@needs_entry
def positions(request, entry):
    name_type = request.POST.get('name', 'abbrev')
    if name_type == 'abbrev':
        get_name = lambda p: p.team.team.abbrev_name
    elif name_type == 'full':
        get_name = lambda p: p.team.team.full_name
    else:
        return { 'error' : 'invalid name type' }

    positions = entry.teams.select_related('team__team')
    result = {}
    for position in positions:
        result[get_name(position)] = position.count
    result['points'] = float(entry.extra_points)

    return result

@csrf_exempt
@needs_entry
def executions(request, entry):
    query = (Q(buy_order__placer=entry.entry_name) | Q(sell_order__placer=entry.entry_name)) & Q(security__market__name=entry.game.name)
    executions = Execution.objects.filter(query).order_by('time').select_related('buy_order').select_related('sell_order').select_related('security')
    result = []
    for execution in executions:
        side = 'BUY' if execution.buy_order.placer == entry.entry_name else 'SELL'
        result.append({
            'time' : str(execution.time),
            'team' : execution.security.name,
            'side' : side,
            'quantity' : execution.quantity,
            'price' : float(execution.price),
        })

    return result

@csrf_exempt
@needs_entry
def open_orders(request, entry):
    result = []
    for order in Order.open_orders.filter(placer=entry.entry_name).select_related('security'):
        result.append({
            'id': order.order_id,
            'team': order.security.name,
            'side': 'BUY' if order.is_buy else 'SELL',
            'quantity': order.quantity_remaining,
            'price': float(order.price),
            'cancel_on_game': order.cancel_on_game
        })

    return result

@csrf_exempt
@needs_entry
def cancel_order(request, entry):
    order_id = request.POST.get('order_id', None)
    if not order_id:
        return { 'error': 'invalid order id' }

    try:
        order = Order.open_orders.get(placer=entry.entry_name, order_id=order_id)
    except Order.DoesNotExist:
        return { 'error': 'invalid order id' }

    order.is_active = False
    order.save()

    return { 'result' : 'success' }
