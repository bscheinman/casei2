from array import array
from ncaacards.models import GameTeam, Team, UserEntry
from django import template
from django.db import connection
from django.utils import timezone
register = template.Library()
import datetime
import random

@register.filter
def get_range(i):
    return range(i)


@register.filter
def underscore(s):
    return s.replace(' ', '_')


@register.filter
def js_bool(b):
    return 'true' if b else 'false'


@register.inclusion_tag('offer_table.html')
def render_offer_table(offer, entry):
    rows = []
    bids, asks = list(offer.bid_side.components.all()), list(offer.ask_side.components.all())
    bid_points, ask_points = offer.bid_side.points, offer.ask_side.points

    if bid_points:
        bids.append(bid_points)
    if ask_points:
        asks.append(ask_points)

    bid_count, ask_count = len(bids), len(asks)
    bid_total, ask_total = 0,0
    for i in range(max(bid_count, ask_count)):
        bid, ask = None, None
        if i < bid_count:
            bid = bids[i]
            if hasattr(bid, 'get_score'): # this is a hacky way of checking for the special case points row
                bid_total += bid.get_score()
            else:
                bid_total += bid
        if i < ask_count:
            ask = asks[i]
            if hasattr(ask, 'get_score'):
                ask_total += ask.get_score()
            else:
                ask_total += ask
        rows.append((bid, ask))

    can_claim, can_cancel = False, False
    if not offer.is_accepted():
        if offer.entry.id != entry.id:
            can_claim = True
        elif offer.is_active:
            can_cancel = True

    return { 'offer':offer, 'rows':rows, 'bid_points':bid_points, 'ask_points':ask_points, 'bid_total':bid_total, 'ask_total':ask_total, 'can_claim':can_claim, 'can_cancel':can_cancel }


@register.inclusion_tag('offer_side.html')
def offer_side(offer_side):
    rows = []
    for component in offer_side.components.all():
        rows.append(component)
    if offer_side.points:
        rows.append(offer_side.points)
    return { 'rows':rows }


@register.inclusion_tag('team_link.html')
def team_link(team_name, game_id=-1, start_tab=''):
    return { 'team_name':team_name, 'game_id':game_id, 'start_tab':start_tab }


@register.inclusion_tag('entry_link.html')
def entry_link(entry):
    return {'entry':entry }


@register.inclusion_tag('entry_link.html')
def entry_name_link(entry_name, game_id):
    entry = None
    try:
        entry = UserEntry.objects.get(game_id=game_id, entry_name=entry_name)
    except UserEntry.DoesNotExist:
        pass
    return { 'entry':entry }


@register.inclusion_tag('game_link.html')
def game_link(game):
    return { 'game':game }


@register.inclusion_tag('leaderboard_table.html')
def leaderboard_table(leaders):
    return { 'leaders':leaders }


@register.inclusion_tag('auth_block.html')
def auth_block(user):
    return { 'user':user }


@register.inclusion_tag('team_select.html')
def team_options(teams):
    return { 'teams':teams }


CI_LOWER = 'case insensitive'
@register.inclusion_tag('ci_text.html')
def ci_text():
    return { 'ci_text' : ''.join([c.upper() if random.randint(0,1) else c for c in CI_LOWER]) }


@register.inclusion_tag('trade_form.html')
def trade_form(game, team=None):
    if team:
        all_team_ids = []
    else:
        all_team_ids = [t.abbrev_name for t in Team.objects.filter(game_type=game.game_type, is_eliminated=False).order_by('abbrev_name')]
    return { 'game':game, 'team':team, 'all_team_ids':all_team_ids }


@register.inclusion_tag('ordercordion.html')
def ordercordion(open_orders, executions, game, self_entry):
    return { 'open_orders':open_orders, 'executions':executions, 'game':game, 'self_entry':self_entry }


@register.inclusion_tag('order_table.html')
def order_table(orders, game, self_entry):
    return { 'orders':orders, 'game':game, 'self_entry':self_entry }


@register.inclusion_tag('stock_execution_table.html')
def execution_table(executions, game, self_entry):
    return { 'executions':executions, 'game':game, 'self_entry':self_entry }

@register.inclusion_tag('order_format.html')
def order_format(order, self_entry, value):
    return { 'is_self_order': (order.entry == self_entry), 'value':value }

UPCOMING_THRESHOLD = datetime.timedelta(days=2)
BASE_FACTOR = 0.3
@register.filter
def upcoming_color(team):
    next_game = team.get_next_game()
    if next_game is None:
        color_scale = 1.0
    else:
        time_until = next_game.game_time - timezone.now()
        if time_until >= UPCOMING_THRESHOLD:
            color_scale = 1.0
        elif time_until <= datetime.timedelta(0):
            color_scale = 0.0
        else:
            color_scale = float(time_until.total_seconds()) / UPCOMING_THRESHOLD.total_seconds()

    gb_value = min(256 * (BASE_FACTOR + color_scale * (1.0 - BASE_FACTOR)), 255)
    return '#FF{0}{0}'.format(hex(int(gb_value))[2:].zfill(2).upper())
