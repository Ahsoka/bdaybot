import os
import argparse

parser = argparse.ArgumentParser(description="Use to set various settings of the bdaybot on runtime.")

parser.add_argument('-db', '--database', default=':memory:')
parser.add_argument('-nt', '--not-testing', action='store_false', dest='testing')
parser.add_argument('-a', '--ASIN', default=os.environ['ASIN'])

args = parser.parse_args()
