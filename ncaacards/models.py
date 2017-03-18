from trading.models import Execution, Market, Order, Security
from django.contrib import admin
from django.contrib.auth.models import User
from django.db import connection, models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging
import string
import uuid

logger = logging.getLogger('ncaacards')

class GameType(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class NcaaGame(models.Model):
    name = models.CharField(max_length=50, unique=True)
    # Storing these in plain text for now
    password = models.CharField(blank=True, null=True, max_length=100)
    position_limit = models.IntegerField(blank=True, null=True)
    points_limit = models.IntegerField(blank=True, null=True)
    game_type = models.ForeignKey(GameType, related_name='games')
    supports_cards = models.BooleanField(default=False)
    supports_stocks = models.BooleanField(default=False)
    settings_locked = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def trade_type_string(self):
        types = []
        if self.supports_cards:
            types.append('Cards')
        if self.supports_stocks:
            types.append('Stocks')
        return string.join(types, ', ')

    def founding_entry(self):
        return self.entries.order_by('join_time')[0]


class ScoreType(models.Model):
    name = models.CharField(max_length=30)
    default_score = models.IntegerField()
    ordering = models.IntegerField() # this is for creating a manual ordering
    game_type = models.ForeignKey(GameType, related_name='score_types')

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('ordering', 'game_type')

class ScoringSetting(models.Model):
    game = models.ForeignKey(NcaaGame)
    scoreType = models.ForeignKey(ScoreType)
    points = models.IntegerField()


class UserEntry(models.Model):
    user = models.ForeignKey(User, related_name='entries')
    game = models.ForeignKey(NcaaGame, related_name='entries')
    entry_name = models.CharField(max_length=30)
    extra_points = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    score = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    join_time = models.DateTimeField(auto_now_add=True)
    apid = models.UUIDField(null=True, default=uuid.uuid4, unique=True)

    class Meta:
        unique_together = ('game', 'entry_name')
    
    def __str__(self):
        return self.entry_name

    def update_score(self):
        points = self.extra_points
        for team in self.teams.all():
            points += team.team.score * team.count
        self.score = points
        self.save()

    def get_positions(self):
        cursor = connection.cursor()
        query = """
            SELECT t.abbrev_name, p.count
                FROM (SELECT * FROM ncaacards_userteam WHERE entry_id = {0}) AS p
                INNER JOIN ncaacards_gameteam AS gt
                    ON p.team_id = gt.id
                INNER JOIN ncaacards_team AS t
                    ON gt.team_id = t.id
        """.format(self.id)
        cursor.execute(query)
        return dict(map(tuple, cursor.fetchall()))


class Team(models.Model):
    full_name = models.CharField(max_length=50)
    abbrev_name = models.CharField(max_length=6)
    game_type = models.ForeignKey(GameType, related_name='teams')
    is_eliminated = models.BooleanField(default=False)

    class Meta:
        unique_together = ('abbrev_name', 'game_type')

    def __str__(self):
        return self.full_name


class GameTeam(models.Model):
    game = models.ForeignKey(NcaaGame)
    team = models.ForeignKey(Team)
    score = models.IntegerField(default=0)
    volume = models.IntegerField(default=0)

    def __str__(self):
        return '%s (%s)' % (self.team.full_name, self.game.name)

    # We could pass in the multipliers for the team to the method so we don't need to make that db call for each game
    def update_score(self):
        points = 0
        counts = self.team.counts
        multipliers = ScoringSetting.objects.filter(game=self.game)
        for scoreType in ScoreType.objects.filter(game_type=self.game.game_type):
            count = counts.get(scoreType=scoreType).count
            multiplier = multipliers.get(scoreType=scoreType).points
            points += count * multiplier
        self.score = points 
        self.save()
        


class TeamScoreCount(models.Model):
    team = models.ForeignKey(Team, related_name='counts')
    scoreType = models.ForeignKey(ScoreType)
    count = models.IntegerField(default=0)

    def __str__(self):
        return '%s-- %s' % (self.team.full_name, self.scoreType.name)


class UserTeam(models.Model):
    entry = models.ForeignKey(UserEntry, related_name='teams')
    team = models.ForeignKey(GameTeam)
    count = models.IntegerField()

    def __str__(self):
        return '%s: %s' % (self.entry.entry_name, self.team.team.abbrev_name)


class TradingBlock(models.Model):
    entry = models.OneToOneField(UserEntry, related_name='trading_block')
    game_teams_desired = models.ManyToManyField(GameTeam, related_name='desired_blocks')
    game_teams_available = models.ManyToManyField(GameTeam, related_name='available_blocks')

    def __str__(self):
        return '%s\'s Trading Block' % self.entry.user.username


class TradeSide(models.Model):
    points = models.IntegerField(blank=True, null=True)


class TradeOffer(models.Model):
    entry = models.ForeignKey(UserEntry, related_name='proposed_trades')
    bid_side = models.OneToOneField(TradeSide, related_name='bid_offer')
    ask_side = models.OneToOneField(TradeSide, related_name='ask_offer')
    accepting_user = models.ForeignKey(UserEntry, blank=True, null=True, related_name='accepted_trades')
    offer_time = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    accept_time = models.DateTimeField(blank=True, null=True)
    cancel_on_game = models.BooleanField(default=False)

    def is_accepted(self):
        return bool(self.accepting_user)


    def __str__(self):
        lines = []
        lines.append('Proposed by %s at %s' % (self.entry.entry_name, self.offer_time))
        if self.is_accepted():
            lines.append('Accepted by %s at %s' % (self.accepting_user.entry_name, self.accept_time))
            lines.append('%s Received:' % self.accepting_user.entry_name)
        else:
            lines.append('%s is Offering:' % self.entry.entry_name)

        for component in self.bid_side.components.all():
            lines.append('\t%s x %s' % (component.team.team.abbrev_name, component.count))
        if self.bid_side.points:
            lines.append('\t%s Points' % self.bid_side.points)

        if self.is_accepted():
            lines.append('%s Received:' % self.entry.entry_name)
        else:
            lines.append('%s is Asking For:' % self.entry.entry_name)

        for component in self.ask_side.components.all():
            lines.append('\t%s x %s' % (component.team.team.abbrev_name, component.count))
        if self.ask_side.points:
            lines.append('\t%s Points' % self.ask_side.points)

        return '<br/>'.join(lines)


class TradeComponent(models.Model):
    team = models.ForeignKey(GameTeam)
    count = models.IntegerField()
    offer = models.ForeignKey(TradeSide, related_name='components')

    def get_score(self):
        return self.count * self.team.score


class LiveGame(models.Model):
    home_team = models.ForeignKey(Team, related_name='home_games')
    away_team = models.ForeignKey(Team, related_name='away_games')
    game_time = models.DateTimeField()
    is_processed = models.BooleanField(default=False)

    def __str__(self):
        return '%s @ %s %s' % (self.away_team.abbrev_name, self.home_team.abbrev_name, self.game_time)


admin.site.register(NcaaGame)
admin.site.register(Team)
admin.site.register(UserTeam)
admin.site.register(ScoreType)
admin.site.register(TradingBlock)
admin.site.register(UserEntry)
admin.site.register(TeamScoreCount)
admin.site.register(GameTeam)
admin.site.register(ScoringSetting)
admin.site.register(TradeOffer)
admin.site.register(TradeSide)
admin.site.register(TradeComponent)
admin.site.register(GameType)
admin.site.register(LiveGame)


def check_position_limits(entry, team):
    game = entry.game
    position_limit = game.position_limit
    if not position_limit:
        return

    team_count = UserTeam.objects.get(entry=entry, team=team).count
    if game.supports_cards:
        bid_components = TradeComponent.objects.filter(offer__bid_offer__is_active=True, offer__bid_offer__entry=entry, team=team)
        for component in bid_components:
            if team_count - component.count < -1 * position_limit:
                offer = component.offer.bid_offer
                offer.is_active = False
                offer.save()
        ask_components = TradeComponent.objects.filter(offer__ask_offer__is_active=True, offer__ask_offer__entry=entry, team=team)
        for component in ask_components:
            if team_count + component.count > position_limit:
                offer = component.offer.ask_offer
                offer.is_active = False
                offer.save()

    if game.supports_stocks:
        orders = Order.open_orders.filter(placer__entry=entry, security__team=team, security__market__game=game)
        for order in orders:
            if (order.is_buy and team_count + order.quantity_remaining > position_limit) or\
                (not order.is_buy and team_count - order.quantity_remaining < -1 * position_limit):
                    order.is_active = False
                    order.save()


def check_point_limits(entry):
    game = entry.game
    points_limit = game.points_limit
    if not points_limit:
        return

    entry_points = entry.extra_points
    if game.supports_cards:
        offers = TradeOffer.objects.filter(entry=entry, is_active=True)
        for offer in offers:
            bid_points = offer.bid_side.points
            if bid_points > 0 and entry_points - bid_points < -1 * points_limit:
                offer.is_active = False
                offer.save()

    if game.supports_stocks:
        orders = Order.open_orders.filter(placer__entry=entry)
        for order in orders:
            if order.is_buy and entry_points - order.price * order.quantity_remaining < -1 * points_limit:
                order.is_active = False
                order.save()


def check_limits(entry, teams):
    game = entry.game
    if game.position_limit:
        for team in teams:
            check_position_limits(entry, team)
    if game.points_limit:
        check_point_limits(entry)


@receiver(post_save, sender=UserEntry, weak=False)
def complete_user_entry(sender, instance, created, **kwargs):
    if created:
        TradingBlock.objects.create(entry=instance)
        for team in GameTeam.objects.filter(game=instance.game):
            UserTeam.objects.create(entry=instance, team=team, count=0)


# Whenever a team's wins are updated, update the score for that team
@receiver(post_save, sender=TeamScoreCount, weak=False)
def update_team_scores(sender, instance, created, **kwargs):
    if not created:
        with transaction.atomic():
            for team in GameTeam.objects.filter(team=instance.team):
                team.update_score()
            for entry in UserEntry.objects.all():
                entry.update_score()


# Update all scores in a game when its scoring settings change
@receiver(post_save, sender=ScoringSetting, weak=False)
def update_game_scores(sender, instance, created, **kwargs):
    if not created:
        game = instance.game
        with transaction.atomic():
            for team in GameTeam.objects.filter(game=game):
                team.update_score()
            for entry in UserEntry.objects.filter(game=game):
                entry.update_score()


@receiver(post_save, sender=NcaaGame, weak=False)
def populate_game(sender, instance, created, **kwargs):
    if created:
        market = Market.objects.create(game=instance, name=instance.name)
        with transaction.atomic():
            for team in Team.objects.filter(game_type=instance.game_type):
                game_team = GameTeam.objects.create(game=instance, team=team)
                Security.objects.create(market=market, team=game_team, name=team.abbrev_name)
            for scoreType in ScoreType.objects.filter(game_type=instance.game_type):
                ScoringSetting.objects.create(game=instance, scoreType=scoreType, points=scoreType.default_score)


@receiver(post_save, sender=Team, weak=False)
def on_new_team(sender, instance, created, **kwargs):
    if created:
        with transaction.atomic():
            for scoreType in ScoreType.objects.filter(game_type=instance.game_type):
                TeamScoreCount.objects.create(team=instance, scoreType=scoreType)
            for game in NcaaGame.objects.filter(game_type=instance.game_type):
                game_team = GameTeam.objects.create(game=game, team=instance)
                for entry in UserEntry.objects.filter(game=game):
                    UserTeam.objects.create(entry=entry, team=game_team, count=0)
                if game.supports_stocks:
                    Security.objects.create(
                        market=Market.objects.filter(game=game)[0], team=game_team, name=instance.abbrev_name)


@receiver(post_save, sender=ScoreType, weak=False)
def create_score_counts(sender, instance, created, **kwargs):
    if created:
        with transaction.atomic():
            for game in NcaaGame.objects.filter(game_type=instance.game_type):
                ScoringSetting.objects.create(game=game, scoreType=instance, points=0)
            for team in Team.objects.filter(game_type=instance.game_type):
                TeamScoreCount.objects.create(team=team, scoreType=instance)


@receiver(post_save, sender=Execution, weak=False)
def record_execution(sender, instance, created, **kwargs):
    if created:
        try:
            with transaction.atomic():
                game = NcaaGame.objects.get(name=instance.security.market.name)
                team = Team.objects.get(abbrev_name=instance.security.name, game_type=game.game_type)
                game_team = GameTeam.objects.get(game=game, team=team)

                transaction_points = instance.quantity * instance.price

                buyer = UserEntry.objects.get(game=game, entry_name=instance.buy_order.placer)
                buyer_count = UserTeam.objects.get(team=game_team, entry=buyer)
                buyer_count.count += instance.quantity
                buyer_count.save()
                buyer.extra_points -= transaction_points
                buyer.update_score()

                seller = UserEntry.objects.get(game=game, entry_name=instance.sell_order.placer)
                seller_count = UserTeam.objects.get(team=game_team, entry=seller)
                seller_count.count -= instance.quantity
                seller_count.save()
                seller.extra_points += transaction_points
                seller.update_score()

                check_limits(buyer, [game_team])
                check_limits(seller, [game_team])

                game_team.volume += instance.quantity
                game_team.save()

        except Exception as e:
            logger.error('Error processing execution %s: %s' % (instance.execution_id, str(e)))
