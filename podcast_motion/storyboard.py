"""The storyboard of the selected part (storyboards/part<N>.py) and its sound cues."""
import importlib

from config import PART
from story import SFX

_part = importlib.import_module(f"storyboards.part{PART}")
SCENES, CHAPTERS, END = _part.SCENES, _part.CHAPTERS, _part.END
HOST_APPEAR, PREVIEW_AT = _part.HOST_APPEAR, _part.PREVIEW_AT
__all__ = ["SCENES", "CHAPTERS", "END", "HOST_APPEAR", "PREVIEW_AT", "SFX"]

# Each scene's elements wait until the previous scene has mostly left the board.
for prev, nxt in zip(SCENES, SCENES[1:]):
    for el in nxt.els:
        el.not_before(prev.end + 0.3)
