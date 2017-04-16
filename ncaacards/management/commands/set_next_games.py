from ncaacards.models import Team
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    
    def handle(self, *args, **kwargs):
        for team in Team.objects.all():
            team.invalidate_next_game()
