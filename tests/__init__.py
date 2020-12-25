# Add bot dir to sys.path
# to avoid ModuleNotFoundError

import sys
import pathlib

two_levels_up = pathlib.Path(__file__).resolve().parents[1]
print(two_levels_up)
sys.path.insert(0, str(two_levels_up))
