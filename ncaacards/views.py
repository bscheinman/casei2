import ncaacards.api.views as api
from ncaacards.forms import ChangeOrderForm, CreateGameForm, TradeForm
from ncaacards.logic import accept_trade, get_leaders, get_game, get_entry, get_team_from_identifier, get_entry_markets
from ncaacards.models import *
from trading.models import Execution, Order, process_order
from cix.views import render_with_request_context
from decimal import Decimal
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
import datetime
import json
import re
import uuid

def get_base_context(request, game_id, **kwargs):
    context = {}
    for key in kwargs:
        context[key] = kwargs[key]
    game, self_entry = None, None
    if game_id:
        game = get_game(game_id)
    context['game'] = game
    if request.user.is_authenticated():
        context['user_games'] = NcaaGame.objects.filter(entries__user=request.user)
        #context['user_entries'] = UserEntry.objects.filter(user=request.user)
        if game:
            context['self_entry'] = get_entry(game, request.user)
    if request.method == 'GET':
        start_tab = request.GET.get('start_tab', '')
        if start_tab:
            context['start_tab'] = start_tab
        context['show_login'] = request.GET.get('show_login', False)
    return context


def home(request):
    entries = []
    if request.user.is_authenticated():
        entries = request.user.entries.all()
    return render_with_request_context(request, 'ncaa_home.html', get_base_context(request, None))


@login_required
def game_home(request, game_id):
    context = get_base_context(request, game_id)

    game = context['game']
    if not game:
        return HttpResponseRedirect('/ncaa/')
    context['leaders'] = get_leaders(game)

    card_executions, stock_executions = [], []
    if game.supports_cards:
        card_executions = TradeOffer.objects.filter(entry__game=game, accepting_user__isnull=False).order_by('-accept_time')[:10]
    if game.supports_stocks:
        stock_executions = Execution.objects.filter(security__market__name=game.name).order_by('-time')[:50]

    context['card_executions'] = card_executions
    context['stock_executions'] = stock_executions

    return render_with_request_context(request, 'game_home.html', context)


@login_required
def entry_view(request, game_id, entry_id):
    game = get_game(game_id)
    self_entry = get_entry(game, request.user)
    if not self_entry:
        return HttpResponseRedirect('/ncaa/')
    
    try:
        entry = UserEntry.objects.get(id=entry_id, game__id=game_id)
    except UserEntry.DoesNotExist:
        return HttpResponseRedirect('/ncaa/game/%s/' % game_id)

    teams = []
    
    teams_query = Q(entry=entry) & (~Q(net_cost=0) | ~Q(count=0))
    user_teams = UserTeam.objects.filter(teams_query).order_by('team__team__abbrev_name')
    for user_team in user_teams:
        team_score = user_team.team.score * user_team.count
        estimated_team_score = user_team.team.estimated_score * user_team.count
        teams.append((user_team.team, user_team.count, team_score, estimated_team_score, user_team.net_cost, estimated_team_score - user_team.net_cost))
    
    card_offers, stock_orders, card_executions, stock_executions = None, None, None, None
    if game.supports_cards:
        card_offers = TradeOffer.objects.filter(entry=self_entry, is_active=True, accepting_user__isnull=True).order_by('-offer_time')
        query = (Q(entry=self_entry) | Q(accepting_user=self_entry)) & Q(accepting_user__isnull=False)
        card_executions = TradeOffer.objects.filter(query).order_by('-offer_time')[:10]
    if game.supports_stocks:
        if entry == self_entry:
            stock_orders = Order.open_orders.filter(entry=entry).order_by('-placed_time').select_related('security', 'entry')
        else:
            stock_orders = []
        query = (Q(buy_order__placer=entry.entry_name) | Q(sell_order__placer=entry.entry_name)) & Q(security__market__name=game.name)
        stock_executions = Execution.objects.filter(query).order_by('-time')[:50]
            

    context = get_base_context(request, game_id, entry=entry, teams=teams,
        card_offers=card_offers, stock_orders=stock_orders, card_executions=card_executions, stock_executions=stock_executions)
    return render_with_request_context(request, 'entry.html', context)


@login_required
def marketplace(request, game_id):
    game = get_game(game_id)
    if not game.supports_cards:
        return HttpResponseRedirect('/ncaa/game/%s/' % game_id)
    entry = get_entry(game, request.user)
    if not entry:
        return HttpResponseRedirect('/ncaa/')
        
    offers_query = Q(entry__game=game, accepting_user=None, is_active=True)

    ask_filter = request.GET.get('ask_filter', '')
    bid_filter = request.GET.get('bid_filter', '')

    if ask_filter:
        offers_query = offers_query & Q(ask_side__components__team__abbrev_name__iexact=ask_filter)
    if bid_filter:
        offers_query = offers_query & Q(bid_side__components__team__abbrev_name__iexact=bid_filter)

    offers = TradeOffer.objects.filter(offers_query).order_by('-offer_time')[:25]
    context = get_base_context(request, game_id, offers=offers)
    return render_with_request_context(request, 'marketplace.html', context)


def team_list(request, game_id):
    context = get_base_context(request, game_id)
    game = context.get('game', None)
    if not game:
        return HttpResponseRedirect('/ncaa/')
    rows = []
    bid_total, ask_total, last_total, volume_total, points_total = Decimal('0.0'), Decimal('0.0'), Decimal('0.0'), 0, 0
    game_teams = GameTeam.objects.filter(game=game).order_by('team__abbrev_name').select_related('team')
    if not request.GET.get('all_teams', False):
        game_teams = game_teams.filter(team__is_eliminated=False)
    if game.supports_stocks:
        securities = Security.objects.filter(market__game=context['game'])
        security_map = { }
        for security in securities:
            security_map[security.name] = security
        for team in game_teams:
            security = security_map[team.team.abbrev_name]
            bid, ask = security.get_bid(), security.get_ask()
            if bid:
                bid_total += bid
            if ask:
                ask_total += ask
            last_total += security.get_last()
            volume_total += team.volume
            points_total += team.score
            rows.append((team, security))
    else:
        for team in game_teams:
            rows.append((team, None))
    context['rows'] = rows
    context['bid_total'] = bid_total
    context['ask_total'] = ask_total
    context['last_total'] = last_total
    context['volume_total'] = volume_total
    context['points_total'] = points_total
    
    return render_with_request_context(request, 'team_list.html', context)


@login_required
def leaderboard(request, game_id):
    game = get_game(game_id)
    entry = get_entry(game, request.user)
    if not entry:
        return HttpResponseRedirect('/ncaa/')

    leaders = get_leaders(game)
    context = get_base_context(request, game_id, leaders=leaders)
    return render_with_request_context(request, 'leaderboard.html', context)


def create_team_context(request, **kwargs):
    team = kwargs['team']
    game = kwargs.get('game', None)

    score_counts_list = []
    score_counts = TeamScoreCount.objects.filter(team=team).order_by('scoreType__ordering')
    if game:
        score_multipliers = ScoringSetting.objects.filter(game=game)

    for score_count in score_counts:
        if game:
            multiplier = score_multipliers.get(scoreType=score_count.scoreType).points
            if multiplier:
                score_counts_list.append((score_count.scoreType.name, score_count.count, score_count.count * multiplier))
        else:
            score_counts_list.append((score_count.scoreType.name, score_count.count))

    context = get_base_context(request, game.id, team=team, score_counts=score_counts_list)
    if game:
        game_team = GameTeam.objects.get(game=game, team=team)

        context['game'] = game
        context['game_team'] = game_team

        top_owners_list = []
        top_owners = UserTeam.objects.filter(team=game_team).order_by('-count')
        
        for owner in top_owners:
            top_owners_list.append((owner.entry, owner.count))
        context['top_owners'] = top_owners_list

        if game.supports_cards:
            offering_trades = TradeOffer.objects.filter(entry__game=game, bid_side__components__team=game_team, accepting_user=None, is_active=True).order_by('-offer_time')
            asking_trades = TradeOffer.objects.filter(entry__game=game, ask_side__components__team=game_team, accepting_user=None, is_active=True).order_by('-offer_time')

            recent_query = Q(entry__game=game) & ~Q(accepting_user=None) & (Q(bid_side__components__team=game_team) | Q(ask_side__components__team=game_team))
            recent_trades = TradeOffer.objects.filter(recent_query).order_by('-accept_time') 
            recent_trade_set = set()
            for trade in recent_trades:
                recent_trade_set.add(trade)

            context['offering_trades'] = offering_trades
            context['asking_trades'] = asking_trades
            context['recent_trades'] = recent_trade_set

        if game.supports_stocks:
            self_entry = context.get('self_entry', '')
            open_orders = []
            if self_entry:
                open_orders = Order.open_orders.filter(entry=self_entry, security__team=game_team).order_by('-placed_time')[:10]
            executions = Execution.objects.filter(security__market__name=game.name, security__name=team.abbrev_name).order_by('-time')[:50]

            context['open_orders'] = open_orders
            context['executions'] = executions

    return context


@login_required
def game_team_view(request, game_id, team_id):
    game = get_game(game_id)
    entry = get_entry(game, request.user)
    if not entry:
        return HttpResponseRedirect('/ncaa/')

    team = get_team_from_identifier(team_id, game.game_type)
    if not team:
        return HttpResponseRedirect('/ncaa/')

    context = create_team_context(request, team=team, game=game)
    context['self_entry'] = entry
    context['security'] = Security.objects.get(team=context['game_team'])
    return render_with_request_context(request, 'team_view.html', context)


MAX_OFFER_SIZE = 5

@login_required
def create_offer(request, game_id, **kwargs):
    game = get_game(game_id)
    if not game.supports_cards:
        return HttpResponseRedirect('/ncaa/game/%s/' % game_id)
    entry = get_entry(game, request.user)
    if not entry:
        return HttpResponseRedirect('/ncaa/')

    all_teams = GameTeam.objects.filter(game=game).order_by('team__abbrev_name')

    error = kwargs.get('error', '')

    context = get_base_context(request, game_id, all_teams=all_teams, max_offer_size=MAX_OFFER_SIZE, error=error)
    return render_with_request_context(request, 'create_offer.html', context)


def create_offer_component(team_name, count_str, game):
    try:
        count = int(count_str)
    except ValueError:
        raise Exception('You must enter a valid integer value for each offer component')

    if bool(team_name) != bool(count):
        raise Exception('All offer components must have both a team and a share count')
    if team_name:
        try:
            team = GameTeam.objects.get(game=game, team__abbrev_name=team_name)
        except GameTeam.DoesNotExist:
            raise Exception('Team %s does not exist in this game' % team_name)

        if count <= 0:
            raise Exception('All component counts must be positive')

        return (team, count)
    return None
    


@login_required
def make_offer(request, game_id):
    game = get_game(game_id)
    if request.method != 'POST' or not game.supports_cards:
        return HttpResponseRedirect('/ncaa/game/%s/' % game_id)

    self_entry = get_entry(game, request.user)
    if not self_entry:
        return HttpResponseRedirect('/ncaa/')

    bids, asks = [], []
    teams_in_offer = set()

    try:
        for i in range(MAX_OFFER_SIZE):
            bid_team_name, bid_count_str = request.POST.get('bid_%s_team' % i, ''), request.POST.get('bid_%s_count' % i, '')
            bid = create_offer_component(bid_team_name, bid_count_str, game)
            if bid:
                bid_team, bid_count = bid
                position = UserTeam.objects.get(entry=self_entry, team=bid_team)
                if bid_team in teams_in_offer:
                    raise Exception('Team %s cannot exist multiple times in the same offer' % bid_team.team.abbrev_name)
                if game.position_limit and position.count - bid_count < -1 * game.position_limit:
                    raise Exception('You tried to offer %s shares of %s but your current position is %s and the position limit is %s'\
                        % (bid_count, bid_team_name, position.count, game.position_limit))
                teams_in_offer.add(bid_team)
                bids.append(bid)
            ask_team_name, ask_count_str = request.POST.get('ask_%s_team' % i, ''), request.POST.get('ask_%s_count' % i, '')
            ask = create_offer_component(ask_team_name, ask_count_str, game)
            if ask:
                ask_team, ask_count = ask
                position = UserTeam.objects.get(entry=self_entry, team=ask_team)
                if ask_team in teams_in_offer:
                    raise Exception('Team %s cannot exist multiple times in the same offer' % ask_team.team.abbrev_name)
                if game.position_limit and position.count + ask_count > game.position_limit:
                    raise Exception('You tried to acquire %s shares of %s but your current position is %s and the position limit is %s'\
                        % (ask_count, ask_team_name, position.count, game.position_limit))
                teams_in_offer.add(ask_team)
                asks.append(ask)

        bid_point_str, ask_point_str = request.POST.get('bid_points', ''), request.POST.get('ask_points', '')
        bid_points, ask_points = 0, 0
        try:
            if bid_point_str:
                bid_points = int(bid_point_str)
                if bid_points < 0:
                    raise Exception('You cannot offer a negative number of points')
                if game.points_limit and self_entry.extra_points - bid_points < -1 * game.points_limit:
                    raise Exception('You tried to offer %s points but you have %s points and the point short limit is %s' %\
                        (bid_point_str, self_entry.extra_points, game.points_limit))
            if ask_point_str:
                ask_points = int(ask_point_str)
                if ask_points < 0:
                    raise Exception('You cannot ask for a negative number of points')
        except ValueError:
            raise Exception('You must enter integer values for points')

        if bid_points and ask_points:
            raise Exception('You can\'t include points on both sides of an offer')

    except Exception as e:
        return create_offer(request, game_id, error=str(e))

    bid_side, ask_side = TradeSide(), TradeSide()
    if bid_points:
        bid_side.points = bid_points
    if ask_points:
        ask_side.points = ask_points
    bid_side.save()
    ask_side.save()

    cancel_on_game = request.POST.get('cancel_on_game', False)
    offer = TradeOffer.objects.create(entry=self_entry, ask_side=ask_side, bid_side=bid_side, cancel_on_game=cancel_on_game)

    for bid_team, bid_count in bids:
        bid_component = TradeComponent.objects.create(team=bid_team, count=bid_count, offer=bid_side)
    for ask_team, ask_count in asks:
        ask_component = TradeComponent.objects.create(team=ask_team, count=ask_count, offer=ask_side)

    return HttpResponseRedirect('/ncaa/game/%s/offer/%s/' % (game_id, offer.id))


@login_required
def offer_view(request, game_id, offer_id):
    game = get_game(game_id)
    self_entry = get_entry(game, request.user)
    if not self_entry:
        return HttpResponseRedirect('/ncaa/')
    try:
        offer = TradeOffer.objects.get(id=offer_id)
    except TradeOffer.DoesNotExist:
        return HttpResponseRedirect('/ncaa/game/%s/' % game_id)

    context = get_base_context(request, game_id, offer=offer)

    return render_with_request_context(request, 'offer_page.html', context)


@login_required
def create_game(request):
    context = get_base_context(request, None, game_types=GameType.objects.all())
    return render_with_request_context(request, 'create_game.html', context)


@login_required
def do_create_game(request):
    if request.method != 'POST':
        return HttpResponseRedirect('/ncaa/')
    errors = []

    form = CreateGameForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data

        game = NcaaGame.objects.create(name=data['game_name'], game_type=data['game_type'],\
            supports_cards=data['support_cards'], supports_stocks=data['support_stocks'])
        game_password = data.get('game_password', '')
        if game_password:
            game.password = game_password
        position_limit = data.get('position_limit', 0)
        points_limit = data.get('points_limit', 0)
        if position_limit:
            game.position_limit = position_limit
        if points_limit:
            game.points_limit = points_limit
        game.save()

        entry = UserEntry.objects.create(game=game, user=request.user, entry_name=data['entry_name'])

        return HttpResponseRedirect('/ncaa/game/%s/scoring_settings/' % game.id)
    else:
        for field in form:
            for e in field.errors:
                errors.append(e)
        context = get_base_context(request, None, game_types=GameType.objects.all(), errors=errors)
        return render_with_request_context(request, 'create_game.html', context)


@login_required
def game_list(request):
    entries = request.user.entries.all()
    query = ~Q(entries__in=entries)
    other_games = NcaaGame.objects.filter(query)
    context = get_base_context(request, None, entries=entries, other_games=other_games)
    return render_with_request_context(request, 'game_list.html', context)


entry_forbidden_regex = re.compile('[^0-9a-zA-Z _]')
@login_required
def join_game(request):
    game_id = request.POST.get('game_id', '')
    entry_name = request.POST.get('entry_name', '')
    password = request.POST.get('password', '')
    otp = None

    game = get_game(game_id)
    if not game or request.method != 'POST':
        return HttpResponseRedirect('/ncaa/')

    error = ''

    if not entry_name:
        error = 'You must provide an entry name'
    elif len(entry_name) > 50:
        error = 'Entry names cannot be longer than 50 characters'
    elif entry_forbidden_regex.search(entry_name):
        error = 'Entry names can only contain letters, numbers, spaces, and underscores'
    else:
        try:
            entry = UserEntry.objects.get(game=game, entry_name=entry_name)
        except UserEntry.DoesNotExist:
            pass
        else:
            error = 'There is already an entry with the name %s in this game' % entry_name

    if game.password and game.password != password:
        try:
            otp = GameOtp.objects.get(game=game, pw=password, active=True)
        except GameOtp.DoesNotExist:
            error = 'Incorrect password'

    self_entry = get_entry(game, request.user)
    if self_entry:
        error = 'You already have an entry in this game'

    if error:
        context = get_base_context(request, game_id, error=error, leaders=get_leaders(game))
        return render_with_request_context(request, 'game_home.html', context)

    with transaction.atomic():
        entry = UserEntry.objects.create(user=request.user, game=game, entry_name=entry_name)
        entry.update_score()

        if otp is not None:
            otp.active = False
            otp.entry = entry
            otp.save()

    return HttpResponseRedirect('/ncaa/game/%s/entry/%s/' % (game_id, entry.id))


@login_required
def accept_offer(request, game_id, offer_id):
    game = get_game(game_id)
    self_entry = get_entry(game, request.user)
    if not self_entry or request.method != 'POST':
        return HttpResponseRedirect('/ncaa/')

    try:
        offer = TradeOffer.objects.get(id=offer_id)
    except TradeOffer.DoesNotExist:
        return HttpResponseRedirect('/ncaa/game/%s/' % game_id)

    error = ''
    try:
        accept_trade(offer, self_entry)
    except Exception as e:
        error = str(e)

    if error:
        context = get_base_context(request, game_id, offer=offer, error=error)
        return render_with_request_context(request, 'offer_page.html', context)

    return HttpResponseRedirect('/ncaa/game/%s/entry/%s/' % (game_id, self_entry.id))


@login_required
def cancel_offer(request, game_id, offer_id):
    try:
        offer = TradeOffer.objects.get(id=offer_id)
    except TradeOffer.DoesNotExist:
        return HttpResponseRedirect('/ncaa/game/%s/' % game_id)

    context = get_base_context(request, game_id, offer=offer)
    self_entry = context.get('self_entry', None)
    if not self_entry:
        return HttpResponseRedirect('/ncaa/')

    error = ''
    if offer.is_accepted():
        error = 'This offer has already been accepted'
    else:
        offer.is_active = False
        offer.save()

    context['error'] = error
    return render_with_request_context(request, 'offer_page.html', context)


@login_required
def leaderboard(request, game_id):
    context = get_base_context(request, game_id)
    if 'self_entry' not in context:
        return HttpResponseRedirect('/ncaa/')
    context['leaders'] = get_leaders(context['game'])
    return render_with_request_context(request, 'leaderboard.html', context)


@login_required
def do_place_order(request, game_id):
    results = { 'success':False, 'errors':[], 'field_errors':{} }
    context = get_base_context(request, game_id)
    self_entry = context.get('self_entry', None)
    if not self_entry:
        results['errors'].append('You cannot place orders for games in which you do not have an entry')
    if request.method != 'POST':
        results['errors'].append('You must use a POST request for submitting orders')

    if not results['errors']:
        results = api.wrap_response(api.do_place_order, request.POST, self_entry)

    return HttpResponse(json.dumps(results))


@login_required
def cancel_order(request, game_id):
    results = { 'success':False, 'errors':[] }
    if request.method != 'POST':
        results['errors'].append('You must use a POST request for cancelling orders')
    else:
        context = get_base_context(request, game_id)
        self_entry = context.get('self_entry', None)
        order_id = request.POST.get('order_id', '')
        if not order_id:
            results['errors'].append('You must provide an order id')
        else:
            try:
                order = Order.orders.get(order_id=order_id)
            except Order.DoesNotExist:
                results['errors'].append('No order exists with the id %s' % order_id)
            else:
                if not self_entry or self_entry.entry_name != order.placer:
                    results['errors'].append('You can only cancel your own orders')

        if not results['errors']:
            order.is_active = False
            order.save()
            results['success'] = True

    return HttpResponse(json.dumps(results))


@login_required
def change_order(request, game_id):
    results = { 'success':False, 'errors':[], 'field_errors':{} }
    if request.method != 'POST':
        results['errors'].append('You must use a POST request for changing orders')
    else:
        try:
            context = get_base_context(request, game_id)
            self_entry = context.get('self_entry', None)
            form = ChangeOrderForm(request.POST)

            if form.is_valid():
                data = form.cleaned_data
                order = Order.orders.get(order_id=data['order_id'])
                price = data.get('price', 0.0)
                quantity = data.get('quantity', 0)
                cancel_on_game = data.get('cancel_on_game', False)

                if price and price != order.price:
                    order.price = price
                    order.last_modified = datetime.datetime.now()
                if quantity:
                    order.quantity_remaining = quantity
                order.cancel_on_game = cancel_on_game
                order.save()
                process_order(order)
                results['success'] = True
            else:
                results['field_errors'] = form.errors

        except Exception as ex:
            results['errors'].append(str(ex))

    return HttpResponse(json.dumps(results))



def add_scoring_context(game, context):
    scoring_settings = ScoringSetting.objects.filter(game=game).order_by('scoreType__ordering')
    context['scoring_settings'] = scoring_settings
    self_entry = context['self_entry']
    context['can_edit'] = self_entry == game.founding_entry() and not game.settings_locked


def scoring_settings(request, game_id):
    context = get_base_context(request, game_id)
    game = context['game']
    if not game:
        return HttpResponseRedirect('/ncaa/')

    add_scoring_context(game, context)
    return render_with_request_context(request, 'scoring_settings.html', context)
    

def save_settings(request, game_id):
    context = get_base_context(request, game_id)
    game = context['game']
    if not game or request.method != 'POST':
        return HttpResponseRedirect('/ncaa/')

    add_scoring_context(game, context)
    if not context['can_edit']:
        return HttpResponseRedirect('/ncaa/game/%s/scoring_settings/' % game_id)

    scoring_settings = ScoringSetting.objects.filter(game=game)
    errors = []
    for setting in scoring_settings:
        setting_str = request.POST.get(setting.scoreType.name.replace(' ', '_'), '')
        if not setting_str:
            continue
        try:
            setting_points = float(setting_str)
        except ValueError:
            errors.append('%s is not a valid score setting' % setting_str)
        else:
            if setting.points != setting_points:
                setting.points = setting_points
                setting.save()

    context['errors'] = errors
    return render_with_request_context(request, 'scoring_settings.html', context)


def lock_settings(request, game_id):
    context = get_base_context(request, game_id)
    game = context['game']
    if not game or request.method != 'POST':
        return HttpResponseRedirect('/ncaa/')

    add_scoring_context(game, context)
    if context['can_edit']:
        game.settings_locked = True
        game.save()

    return HttpResponseRedirect('/ncaa/game/%s/scoring_settings/' % game_id)


def market_maker(request, game_id):
    context = get_base_context(request, game_id)
    game = context.get('game', None)
    self_entry = context.get('self_entry', None)
    if not game or not self_entry or not game.supports_stocks:
        return HttpResponseRedirect('/ncaa/')

    rows = []
    markets = get_entry_markets(self_entry)

    for market in markets:
        rows.append((market['team'], market['security'], market['position'], market['user_bid'], market['user_ask']))

    context['rows'] = rows
    
    return render_with_request_context(request, 'market_maker.html', context)

def do_make_market(request, game_id):
    context = get_base_context(request, game_id)
    game = context.get('game', None)
    self_entry = context.get('self_entry', None)
    if not game or not self_entry or request.method != 'POST' or not game.supports_stocks:
        return HttpResponseRedirect('/ncaa/')

    errors = []
    game_teams = GameTeam.objects.filter(game=game, team__is_eliminated=False).order_by('team__abbrev_name').select_related('team')
    securities = Security.objects.filter(market__game=context['game'])
    security_map = {}
    for security in securities:
        security_map[security.name] = security

    try:
        with transaction.atomic():
            for team in game_teams:
                do_edit = request.POST.get('apply_team_%s' % team.team.abbrev_name, False)
                if not do_edit:
                    continue

                security = security_map[team.team.abbrev_name]
                try:
                    api.do_make_market(request, self_entry, security, team.team.abbrev_name)
                except ApiException as e:
                    errors += ['{0}: {1}'.format(team.team.abbrev_name, err) for err in e.errors]

            if errors:
                raise Exception

    except Exception as e:
        pass

    results = { 'success' : len(errors) == 0, 'errors' : errors }

    return HttpResponse(json.dumps(results))
