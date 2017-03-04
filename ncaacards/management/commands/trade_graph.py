from casei.ncaacards.models import NcaaGame, UserEntry
from casei.trading.models import Execution
import collections
from django.core.management.base import NoArgsCommand
import pygraphviz as gv

class Command(NoArgsCommand):

    args = '<game_name>'

    def handle(self, *args, **options):
        edges = collections.defaultdict(int)
        game = NcaaGame.objects.get(name=args[0])
        entry_scores = dict([(entry.entry_name, entry.score) for entry in UserEntry.objects.filter(game=game)])

        for execution in Execution.objects.filter(security__market__game=game):
            trade_delta = execution.quantity * (execution.security.team.score - execution.price)
            buyer_name = execution.buy_order.entry.entry_name
            seller_name = execution.sell_order.entry.entry_name

            if buyer_name < seller_name:
                edge_key = (buyer_name, seller_name)
                trade_coeff = 1
            else:
                edge_key = (seller_name, buyer_name)
                trade_coeff = -1

            edges[edge_key] += trade_coeff * trade_delta

        trade_graph = gv.AGraph(strict=True, directed=True)
        for entry, score in entry_scores.iteritems():
            #trade_graph.add_node(entry, label='%s: %s' % (entry, str(score)))
            trade_graph.add_node(entry)
        for entries, weight in edges.iteritems():
            if weight > 0:
                entries = (entries[1], entries[0])
            else:
                weight = -1 * weight
            trade_graph.add_edge(*entries, label=str(weight))

        trade_graph.write('graph.dot')
        trade_graph.layout(prog='dot')
        trade_graph.draw('graph.png')
