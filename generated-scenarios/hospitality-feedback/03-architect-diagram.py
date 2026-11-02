"""Regenerate the target-parameterized reference architecture diagram."""
from pathlib import Path
from scripts.draw_diagrams import draw

if __name__ == "__main__":
    draw("architecture", Path(__file__).with_suffix(".png"))
