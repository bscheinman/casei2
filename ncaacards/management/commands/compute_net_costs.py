from ncaacards.models import UserTeam
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    
    def handle(self, *args, **kwargs):
        for user_team in UserTeam.objects.all():
            user_team.recompute_net_cost()
