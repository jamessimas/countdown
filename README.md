# Countdown Timer

A small CLI countdown timer built with the Python standard library.

It accepts a single duration argument, shows a live countdown in the terminal, and when time is up it rings the terminal bell until you press:

- `r` to restart the same timer
- `q` to quit

On macOS, it can send a system notification when the timer finishes.

## Usage

Run:

```
python3 countdown.py [-q|--quiet] LENGTH
```

Examples:

```bash
python3 countdown.py 10s     # 10 seconds
python3 countdown.py 5m      #  5 minutes
python3 countdown.py 2h      #  2 hours
```

## Unit Tests

Run all tests:

```bash
python3 -m unittest -v
```
