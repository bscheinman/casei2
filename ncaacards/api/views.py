from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from ncaacards.forms import TradeForm
from ncaacards.logic import get_team_from_identifier
from ncaacards.models import *
from trading.models import Execution, Order
import json

def set_response_result(resp, result):
    resp['result'] = result

def set_response_error(resp, err):
    resp['errors'].append(err)
    resp['success'] = False

def create_base_response():
    return { 'success': True, 'errors': [] }

def create_success_response(result):
    resp = create_base_response()
    set_response_result(resp, result)
    return resp

def create_error_response(err):
    resp = create_base_response()
    set_response_error(resp, err)
    return resp

def needs_entry(fn):
    def wrapper(request):
        apid_str = request.POST.get('apid', None)
        if not apid_str:
            resp = create_error_response('invalid apid')
        else:
            try:
                apid = uuid.UUID(apid_str)
                entry = UserEntry.objects.get(apid=apid)
            except:
                resp = create_error_response('invalid apid')
            else:
                resp = fn(request, entry)

        return HttpResponse(json.dumps(resp))

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
        return create_error_response('invalid name type')

    positions = entry.teams.select_related('team__team')
    result = {}
    for position in positions:
        result[get_name(position)] = position.count
    result['points'] = float(entry.extra_points)

    return create_success_response(result)

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

    return create_success_response(result)

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

    return create_success_response(result)

@csrf_exempt
@needs_entry
def cancel_order(request, entry):
    order_id = request.POST.get('order_id', None)
    if not order_id:
        return create_error_response('invalid order id')

    try:
        order = Order.open_orders.get(placer=entry.entry_name, order_id=order_id)
    except Order.DoesNotExist:
        return create_error_response('invalid order id')

    order.is_active = False
    order.save()

    return create_base_response()

def do_place_order(params, self_entry):
    response = create_base_response()
    game = self_entry.game

    if not game.supports_stocks:
        set_response_error(response, 'This game does not support stock-style trading')
        return response

    form = TradeForm(params)
    if not form.is_valid():
        for field, err in form.errors.iteritems():
            set_response_error(response, err)
        return response

    data = form.cleaned_data

    try:
        team = get_team_from_identifier(data['team_identifier'], game.game_type)
        game_team = GameTeam.objects.get(game=game, team=team)
        if not game_team:
            raise Exception('There is no team with the ID %s' % team_id)
        position = UserTeam.objects.get(entry=self_entry, team=game_team)

        is_buy = data['side'] == 'buy'
        quantity = data['quantity']
        price = data['price']
        total_order_points = quantity * price
        if is_buy:
            if game.position_limit and quantity + position.count > game.position_limit:
                raise Exception('You tried to buy %s shares of %s but your current position is %s shares and the position limit is %s' %\
                    (quantity, team.abbrev_name, position.count, game.position_limit))
            if game.points_limit and self_entry.extra_points - total_order_points < -1 * game.points_limit:
                raise Exception('This order would cost %s but you have %s raw points and the points short limit is %s' %\
                    (total_order_points, self_entry.extra_points, game.points_limit))
        else:
            if game.position_limit and position.count - quantity < -1 * game.position_limit:
                raise Exception('You tried to sell %s shares of %s but your current position is %s shares and the position limit is %s' %\
                    (quantity, team.abbrev_name, position.count, game.position_limit))

        order = Order.orders.create(entry=self_entry, placer=self_entry.entry_name, security=Security.objects.get(team=game_team),\
            price=price, quantity=quantity, quantity_remaining=quantity, is_buy=is_buy, cancel_on_game=data['cancel_on_game'])

        set_response_result(response, { 'order_id': order.order_id })

    except Exception as error:
        set_response_error(response, str(error))

    return response

@csrf_exempt
@needs_entry
def place_order(request, entry):
    return do_place_order(request.POST, entry)
