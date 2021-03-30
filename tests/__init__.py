import sys
import pathlib

# Add bot dir to sys.path
# to avoid ModuleNotFoundError
two_levels_up = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(two_levels_up))
