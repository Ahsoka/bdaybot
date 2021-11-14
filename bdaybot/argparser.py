import argparse

class IgnoreUnrecognizedArgs(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        return self.parse_known_args(args, namespace)[0]

parser = IgnoreUnrecognizedArgs(
    description="Use to set various settings of the bdaybot on runtime.",
    add_help=False
)

parser.add_argument('-db', '--database', default='sqlite+aiosqlite:///:memory:')
parser.add_argument('-nt', '--not-testing', action='store_false', dest='testing')
parser.add_argument('-a', '--ASIN')
parser.add_argument('-po', '--place-order', action='store_true', dest='place_order')
parser.add_argument('-pe', '--print-envelope', action='store_true', dest='print_envelope')
parser.add_argument('-t', '--token')
parser.add_argument('-dmo', '--DM-owner', action='store_true', dest='DM_owner')
