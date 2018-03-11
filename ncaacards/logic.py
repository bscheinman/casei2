from ncaacards.models import check_limits, NcaaGame, Team, TradeComponent, UserEntry, UserTeam, GameTeam
from trading.models import Security
from django.db.models import Q
import datetime

def get_game(game_id):
    try:
        return NcaaGame.objects.get(id=game_id)
    except NcaaGame.DoesNotExist:
        return None


def get_entry(game, user):  
    try:
        return UserEntry.objects.get(game=game, user=user)
    except UserEntry.DoesNotExist:
        return None


def get_leaders(game, estimated=True):
    sorter = '-estimated_score' if estimated else '-score'
    return UserEntry.objects.filter(game=game).order_by(sorter)


def apply_trade_side(components, points, entry, holdings, addOrRemove):
    for component in components:
        holding = holdings.get(team=component.team)
        if addOrRemove:
            holding.count += component.count
            component.team.volume += component.count
            component.team.save()
        else:
            holding.count -= component.count
        holding.save()
    if points:
        if addOrRemove:
            entry.extra_points += points
        else:
            entry.extra_points -= points
        entry.save()
        

def validate_trade_side(components, entry, positions, is_buying, position_limit):
    for component in components:
        position = positions.get(team=component.team)
        if is_buying:
            if position.count + component.count > position_limit:
                raise Exception('%s would acquire %s shares of %s but their current position is %s and the position limit is %s' %\
                    (entry.entry_name, component.count, component.team.team.abbrev_name, position.count, position_limit))
        else:
            if position.count - component.count < -1 * position_limit:
                raise Exception('%s would give up %s shares of %s but their current position is %s and the position limit is %s' %\
                    (entry.entry_name, component.count, component.team.team.abbrev_name, position.count, position_limit))


def accept_trade(trade, accepting_entry):
    if trade.is_accepted():
        raise Exception('Trade has already been accepted')

    if accepting_entry == trade.entry:
        raise Exception('Users cannot accept their own trades')

    bid_components = trade.bid_side.components.all()
    ask_components = trade.ask_side.components.all()
    
    bid_points = trade.bid_side.points
    ask_points = trade.ask_side.points

    seller = trade.entry
    buyer = accepting_entry

    seller_holdings = seller.teams.all()
    buyer_holdings = buyer.teams.all()

    position_limit = seller.game.position_limit
    if position_limit:
        validate_trade_side(bid_components, seller, seller_holdings, False, position_limit)
        validate_trade_side(bid_components, buyer, buyer_holdings, True, position_limit)
        validate_trade_side(ask_components, seller, seller_holdings, True, position_limit)
        validate_trade_side(ask_components, buyer, buyer_holdings, False, position_limit)

    if trade.entry.game.points_limit:
        points_short_limit = -1 * trade.entry.game.points_limit
        points_error_info = None
        if ask_points > 0:
            if buyer.extra_points - ask_points < points_short_limit:
                points_error_info = (buyer.entry_name, ask_points, buyer.extra_points, points_short_limit)
        elif ask_points and ask_points < 0:
            if seller.extra_points + ask_points < points_short_limit:
                points_error_info = (seller.entry_name, ask_points, seller.extra_points, points_short_limit)
        elif bid_points > 0:
            if seller.extra_points - bid_points < points_short_limit:
                points_error_info = (seller.entry_name, bid_points, seller.extra_points, points_short_limit)
        elif bid_points and bid_points < 0:
            if buyer.extra_points + bid_points < points_short_limit:
                points_error_info = (buyer.entry_name, bid_points, buyer.extra_points, points_short_limit)
        
        if points_error_info:
            raise Exception('%s would give up %s points but they have %s and the points short limit is %s' % points_error_info)
            

    apply_trade_side(bid_components, bid_points, seller, seller_holdings, False)
    apply_trade_side(ask_components, ask_points, buyer, buyer_holdings, False)
    apply_trade_side(bid_components, bid_points, buyer, buyer_holdings, True)
    apply_trade_side(ask_components, ask_points, seller, seller_holdings, True)
    trade.accepting_user = accepting_entry
    trade.accept_time = datetime.datetime.now()
    trade.save()

    teams = []
    for component in bid_components:
        teams.append(component.team)
    for component in ask_components:
        teams.append(component.team)
    check_limits(buyer, teams)
    check_limits(seller, teams)

    trade.entry.update_score()
    accepting_entry.update_score()


def get_team_from_identifier(team_id, game_type):
    team_query = Q(game_type=game_type)
    try:
        num_id = int(team_id)
        team_query = team_query & Q(id=num_id)
    except ValueError:
        team_query = team_query & (Q(abbrev_name__iexact=team_id) | Q(full_name__iexact=team_id))

    try:
        return Team.objects.get(team_query)
    except Team.DoesNotExist:
        return None


def get_entry_markets(entry):
    rows = []
    game_teams = GameTeam.objects.filter(game=entry.game, team__is_eliminated=False).order_by('team__abbrev_name').select_related('team')
    securities = Security.objects.filter(market__game=entry.game)
    positions = { position.team_id: position.count for position in UserTeam.objects.filter(entry=entry) }
    security_map = {}
    for security in securities:
        security_map[security.name] = security
    for team in game_teams:
        security = security_map[team.team.abbrev_name]
        position = positions[team.id]
        user_bid = security.get_bid_order(entry)
        user_ask = security.get_ask_order(entry)
        rows.append({
            'team': team,
            'security': security,
            'position': position,
            'user_bid': user_bid,
            'user_ask': user_ask
        })

    return rows
