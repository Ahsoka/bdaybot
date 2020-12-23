import os
import argparse

parser = argparse.ArgumentParser(description="Use to set various settings of the bdaybot on runtime.")

parser.add_argument('-db', '--database', default='sqlite:///:memory:')
parser.add_argument('-nt', '--not-testing', action='store_false', dest='testing')
parser.add_argument('-a', '--ASIN', default=os.environ['ASIN'])
parser.add_argument('-po', '--place-order', action='store_true', dest='place_order')
parser.add_argument('-pe', '--print-envelope', action='store_true', dest='print_envelope')
parser.add_argument('-t', '--token')
