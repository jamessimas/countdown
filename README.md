# Countdown Timer

A small CLI countdown timer built with the Python standard library.

It accepts a single duration argument, shows a live countdown in the terminal, and when time is up it rings the terminal bell until you press:

- `r` to restart the same timer
- `q` to quit

On macOS, it can send a system notification when the timer finishes.

## Usage

Run:

```bash
python3 countdown.py [-q|--quiet] LENGTH
```

`LENGTH` examples:

- `10m` (10 minutes)
- `5s` (5 seconds)
- `1h` (1 hour)
- `30` (30 seconds; default unit is seconds)

`-q` / `--quiet` disables the macOS notification.

## Unit Tests

Run all tests with:

```bash
python3 -m unittest -v
```
