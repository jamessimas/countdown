import argparse
import unittest
from unittest import mock

import countdown


class ParseDurationTests(unittest.TestCase):
    def test_parse_duration_valid_values(self):
        cases = {
            "10m": 600,
            "5s": 5,
            "1h": 3600,
            "30": 30,
            " 7M ": 420,
            "2H": 7200,
        }

        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(countdown.parse_duration(value), expected)

    def test_parse_duration_invalid_values(self):
        cases = ["", "abc", "10x", "-5", "0", "0m"]

        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    countdown.parse_duration(value)


class FormatHmsTests(unittest.TestCase):
    def test_format_hms_outputs_expected(self):
        self.assertEqual(countdown.format_hms(0), "00:00:00")
        self.assertEqual(countdown.format_hms(5), "00:00:05")
        self.assertEqual(countdown.format_hms(65), "00:01:05")
        self.assertEqual(countdown.format_hms(3661), "01:01:01")


class NormalizeDurationLabelTests(unittest.TestCase):
    def test_normalize_duration_label_with_and_without_units(self):
        self.assertEqual(countdown.normalize_duration_label("5s"), "5s")
        self.assertEqual(countdown.normalize_duration_label("1H"), "1h")
        self.assertEqual(countdown.normalize_duration_label(" 10m "), "10m")
        self.assertEqual(countdown.normalize_duration_label("30"), "30s")

    def test_normalize_duration_label_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            countdown.normalize_duration_label("bad")


class RenderCountdownTests(unittest.TestCase):
    def test_render_countdown_writes_progress_line(self):
        fake_stdout = mock.Mock()

        with mock.patch.object(countdown.sys, "stdout", fake_stdout):
            countdown.render_countdown(10, 5)

        fake_stdout.write.assert_called_once_with(
            "\r[===============---------------] 00:00:05 remaining"
        )
        fake_stdout.flush.assert_called_once_with()


class RunCountdownTests(unittest.TestCase):
    def test_run_countdown_renders_until_zero_and_finishes_line(self):
        fake_stdout = mock.Mock()

        with (
            mock.patch.object(countdown.sys, "stdout", fake_stdout),
            mock.patch.object(countdown, "render_countdown") as render_mock,
            mock.patch.object(countdown.time, "sleep") as sleep_mock,
            mock.patch.object(
                countdown.time, "monotonic", side_effect=[100.0, 100.0, 101.2, 102.3]
            ),
        ):
            countdown.run_countdown(2)

        self.assertEqual(render_mock.call_args_list[0], mock.call(2, 2))
        self.assertEqual(render_mock.call_args_list[1], mock.call(2, 1))
        self.assertEqual(render_mock.call_args_list[2], mock.call(2, 0))
        self.assertEqual(sleep_mock.call_count, 2)
        fake_stdout.write.assert_called_once_with("\n")
        fake_stdout.flush.assert_called_once_with()


class SendMacosNotificationTests(unittest.TestCase):
    def test_send_macos_notification_runs_osascript_on_macos(self):
        with (
            mock.patch.object(countdown.sys, "platform", "darwin"),
            mock.patch.object(countdown.subprocess, "run") as run_mock,
        ):
            countdown.send_macos_notification("5s")

        run_mock.assert_called_once_with(
            [
                "osascript",
                "-e",
                'display notification "5s timer done." with title "Countdown"',
            ],
            check=False,
            stdout=countdown.subprocess.DEVNULL,
            stderr=countdown.subprocess.DEVNULL,
        )

    def test_send_macos_notification_is_noop_on_non_macos(self):
        with (
            mock.patch.object(countdown.sys, "platform", "linux"),
            mock.patch.object(countdown.subprocess, "run") as run_mock,
        ):
            countdown.send_macos_notification("5s")

        run_mock.assert_not_called()

    def test_send_macos_notification_handles_osascript_failure(self):
        with (
            mock.patch.object(countdown.sys, "platform", "darwin"),
            mock.patch.object(
                countdown.subprocess, "run", side_effect=OSError("missing")
            ),
        ):
            countdown.send_macos_notification("5s")


class WaitForAlarmCommandTests(unittest.TestCase):
    def test_wait_for_alarm_command_non_tty_restarts(self):
        fake_stdout = mock.Mock()
        fake_stdin = mock.Mock()
        fake_stdin.isatty.return_value = False

        with (
            mock.patch.object(countdown.sys, "stdout", fake_stdout),
            mock.patch.object(countdown.sys, "stdin", fake_stdin),
            mock.patch("builtins.input", side_effect=["x", "r"]),
        ):
            result = countdown.wait_for_alarm_command()

        self.assertEqual(result, "restart")
        self.assertEqual(fake_stdout.write.call_count, 2)
        self.assertEqual(fake_stdout.flush.call_count, 2)

    def test_wait_for_alarm_command_tty_quits_and_restores_terminal(self):
        fake_stdout = mock.Mock()
        fake_stdin = mock.Mock()
        fake_stdin.isatty.return_value = True
        fake_stdin.fileno.return_value = 99
        fake_stdin.read.return_value = "q"

        with (
            mock.patch.object(countdown.sys, "stdout", fake_stdout),
            mock.patch.object(countdown.sys, "stdin", fake_stdin),
            mock.patch.object(
                countdown.termios, "tcgetattr", return_value=["orig"]
            ) as tcgetattr_mock,
            mock.patch.object(countdown.tty, "setcbreak") as setcbreak_mock,
            mock.patch.object(
                countdown.select, "select", return_value=([fake_stdin], [], [])
            ),
            mock.patch.object(countdown.time, "monotonic", return_value=1.0),
            mock.patch.object(countdown.termios, "tcsetattr") as tcsetattr_mock,
        ):
            result = countdown.wait_for_alarm_command()

        self.assertEqual(result, "quit")
        tcgetattr_mock.assert_called_once_with(99)
        setcbreak_mock.assert_called_once_with(99)
        tcsetattr_mock.assert_called_once_with(
            99, countdown.termios.TCSADRAIN, ["orig"]
        )


class BuildParserTests(unittest.TestCase):
    def test_build_parser_parses_valid_length(self):
        parser = countdown.build_parser()
        args = parser.parse_args(["5m"])
        self.assertEqual(args.length, 300)
        self.assertFalse(args.quiet)

    def test_build_parser_parses_quiet_flag(self):
        parser = countdown.build_parser()
        args = parser.parse_args(["-q", "5m"])
        self.assertTrue(args.quiet)
        self.assertEqual(args.length, 300)

    def test_build_parser_rejects_invalid_length(self):
        parser = countdown.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["bad"])


class MainTests(unittest.TestCase):
    def test_main_sends_notification_by_default(self):
        with (
            mock.patch.object(countdown, "clear_screen"),
            mock.patch.object(countdown, "run_countdown"),
            mock.patch.object(countdown, "wait_for_alarm_command", return_value="quit"),
            mock.patch.object(countdown, "send_macos_notification") as notify_mock,
        ):
            result = countdown.main(["5s"])

        self.assertEqual(result, 0)
        notify_mock.assert_called_once_with("5s")

    def test_main_suppresses_notification_when_quiet(self):
        with (
            mock.patch.object(countdown, "clear_screen"),
            mock.patch.object(countdown, "run_countdown"),
            mock.patch.object(countdown, "wait_for_alarm_command", return_value="quit"),
            mock.patch.object(countdown, "send_macos_notification") as notify_mock,
        ):
            result = countdown.main(["-q", "5s"])

        self.assertEqual(result, 0)
        notify_mock.assert_not_called()

    def test_main_clears_screen_only_on_first_run(self):
        tracker = mock.Mock()

        with (
            mock.patch.object(
                countdown, "clear_screen", side_effect=tracker.clear_screen
            ),
            mock.patch.object(
                countdown, "run_countdown", side_effect=tracker.run_countdown
            ),
            mock.patch.object(
                countdown,
                "wait_for_alarm_command",
                side_effect=["restart", "quit"],
            ),
            mock.patch.object(
                countdown,
                "send_macos_notification",
                side_effect=tracker.send_macos_notification,
            ),
        ):
            result = countdown.main(["5s"])

        self.assertEqual(result, 0)
        self.assertEqual(tracker.clear_screen.call_count, 1)
        self.assertEqual(tracker.run_countdown.call_count, 2)
        self.assertEqual(tracker.send_macos_notification.call_count, 2)
        self.assertEqual(
            tracker.mock_calls,
            [
                mock.call.clear_screen(),
                mock.call.run_countdown(5),
                mock.call.send_macos_notification("5s"),
                mock.call.run_countdown(5),
                mock.call.send_macos_notification("5s"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
