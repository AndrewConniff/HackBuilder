"""Refresh public Azure prices only; no private scenario information is sent."""

import importlib.util
import sys
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
SCENARIO = DIRECTORY.parent.parent
SOURCE = SCENARIO / ".worker/04aeed2e81f44650b04cfe74fce03cd6/collect_prices.py"
spec = importlib.util.spec_from_file_location("public_prices", SOURCE)
prices = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prices)
prices.DIRECTORY = DIRECTORY
prices.FILTERS = {
    key: value.replace("eastus", "centralus")
    for key, value in prices.FILTERS.items() if key != "hosting-alternative"
}
sys.argv = [sys.argv[0]]
prices.main()
