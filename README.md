# MS-ML-Bot
Maplestory Machine Learning Bot

## Setup

Requires Windows and **Python 3.13 (64-bit)** installed with the **tcl/tk** option (needed for the GUI).
An NVIDIA GPU (RTX 20-series or newer) is recommended; PyTorch is pinned to the CUDA 13.0 build, which only needs an up-to-date NVIDIA driver (no CUDA Toolkit install).

```
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e . --no-deps
```

The last command registers the project's packages (`gui`, `data`, `process`, `tools`, `yolov5`) so scripts can be run directly from an IDE.
Re-run it if the repository folder moves. For linting/formatting tools, install `requirements-dev.txt` instead of `requirements.txt`.

The YOLOv5 code is fetched by `torch.hub` on first run, pinned to a specific commit in `yolov5/model.py`, and cached in `%USERPROFILE%\.cache\torch\hub`.

## Running

Run from the repository root, as administrator (the game ignores input from non-elevated processes):

```
.venv\Scripts\python.exe -m process.bootstrapper
```

In the app's Application panel, set the window name to the game window's title (e.g. `MapleStory`).

## Configuration

Tunable values (read rates, player search, potion timing, display) are in [`config.toml`](config.toml), with a comment explaining each one.
Edit it and restart the app; anything missing or invalid falls back to its default.
