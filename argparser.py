import argparse

parser = argparse.ArgumentParser(description="Use to set various settings of the bdaybot on runtime.")

parser.add_argument('-db', '--database', default='bdaybot.db')
parser.add_argument('-nt', '--not-testing', action='store_false', dest='testing')

args = parser.parse_args()
