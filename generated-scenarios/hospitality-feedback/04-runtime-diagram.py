"""Regenerate the runtime and failure-path diagram."""
from pathlib import Path
from scripts.draw_diagrams import draw

if __name__ == "__main__":
    draw("runtime", Path(__file__).with_suffix(".png"))
