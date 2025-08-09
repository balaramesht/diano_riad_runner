# Dino Runner (Chrome Offline-Style) in Python

A lightweight clone of Chrome's offline T‑Rex runner built with Pygame. No external assets are required; everything is rendered as simple shapes for portability.

## Requirements
- Python 3.9+
- Pygame

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run
```bash
python dino_runner.py
```

## Controls
- Space / Up Arrow: Jump
- Down Arrow: Duck
- R: Restart after game over
- Q or Esc: Quit

## Notes
- Game speed increases as you score.
- Obstacles spawn with variable sizes and spacing, similar to the Chrome dino game.
- If running on a headless server, you may need a virtual display (e.g., xvfb) to launch Pygame windows.
