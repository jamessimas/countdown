#!/usr/bin/env python3

import argparse
import re
import select
import sys
import termios
import time
import tty


UNIT_MULTIPLIERS = {
    "": 1,
    "s": 1,
    "m": 60,
    "h": 3600,
}


def parse_duration(value):
    match = re.fullmatch(r"\s*(\d+)\s*([hmsHMS]?)\s*", value)
    if not match:
        raise argparse.ArgumentTypeError(
            "invalid timer length; use formats like 10m, 5s, 1h, or 30"
        )

    amount = int(match.group(1))
    unit = match.group(2).lower()

    if amount <= 0:
        raise argparse.ArgumentTypeError("timer length must be greater than zero")

    return amount * UNIT_MULTIPLIERS[unit]


def format_hms(total_seconds):
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return "{0:02d}:{1:02d}:{2:02d}".format(hours, minutes, seconds)


def render_countdown(total_seconds, remaining_seconds):
    bar_width = 30
    elapsed = total_seconds - remaining_seconds
    ratio = elapsed / float(total_seconds)
    filled = int(ratio * bar_width)
    bar = "=" * filled + "-" * (bar_width - filled)

    line = "\r[{0}] {1} remaining".format(bar, format_hms(remaining_seconds))
    sys.stdout.write(line)
    sys.stdout.flush()


def run_countdown(total_seconds):
    end_time = time.monotonic() + total_seconds

    while True:
        remaining = int(end_time - time.monotonic() + 0.999)
        if remaining < 0:
            remaining = 0

        render_countdown(total_seconds, remaining)
        if remaining == 0:
            break

        time.sleep(0.1)

    sys.stdout.write("\n")
    sys.stdout.flush()


def wait_for_alarm_command():
    prompt = "Time is up! Press [r] to restart or [c] to close."

    if not sys.stdin.isatty():
        while True:
            sys.stdout.write("\a")
            sys.stdout.flush()
            choice = (
                input("Time is up! Type 'r' to restart or 'c' to close: ")
                .strip()
                .lower()
            )
            if choice == "c":
                return "close"
            if choice == "r":
                return "restart"

    fd = sys.stdin.fileno()
    original_settings = termios.tcgetattr(fd)
    next_bell = 0.0

    try:
        tty.setcbreak(fd)

        while True:
            now = time.monotonic()
            if now >= next_bell:
                sys.stdout.write("\a")
                sys.stdout.flush()
                next_bell = now + 0.8

            sys.stdout.write("\r" + prompt + " ")
            sys.stdout.flush()

            readable, _, _ = select.select([sys.stdin], [], [], 0.1)
            if readable:
                char = sys.stdin.read(1).lower()
                if char == "c":
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return "close"
                if char == "r":
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return "restart"
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original_settings)


def build_parser():
    parser = argparse.ArgumentParser(description="Simple countdown timer")
    parser.add_argument(
        "length",
        type=parse_duration,
        help="timer length (examples: 10m, 5s, 1h, 30)",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    total_seconds = args.length

    while True:
        run_countdown(total_seconds)
        action = wait_for_alarm_command()
        if action == "close":
            return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        sys.stdout.write("\nInterrupted.\n")
        sys.stdout.flush()
        raise SystemExit(130)
