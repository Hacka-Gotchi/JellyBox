"""Tests for the command runner.

Uses only universally-available commands (echo, sleep, printf) so it runs
anywhere without special tools installed.
"""
import time
import unittest

from core.command_runner import CommandRunner


class TestCommandRunnerSync(unittest.TestCase):
    def setUp(self):
        self.runner = CommandRunner()

    def test_echo(self):
        r = self.runner.run(["echo", "hello"])
        self.assertTrue(r.ok)
        self.assertEqual(r.returncode, 0)
        self.assertIn("hello", r.stdout)

    def test_missing_binary(self):
        r = self.runner.run(["definitely-not-a-real-binary-xyz"])
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "not found")

    def test_timeout(self):
        r = self.runner.run(["sleep", "5"], timeout=0.2)
        self.assertTrue(r.timed_out)
        self.assertFalse(r.ok)

    def test_nonzero_exit(self):
        r = self.runner.run(["sh", "-c", "exit 3"])
        self.assertEqual(r.returncode, 3)
        self.assertFalse(r.ok)


class TestCommandRunnerAsync(unittest.TestCase):
    def setUp(self):
        self.runner = CommandRunner()

    def _wait(self, task, timeout=5.0):
        deadline = time.monotonic() + timeout
        while not task.finished and time.monotonic() < deadline:
            time.sleep(0.01)

    def test_streaming_and_result(self):
        task = self.runner.run_async(["printf", "a\\nb\\nc\\n"])
        self._wait(task)
        self.assertTrue(task.finished)
        lines = task.drain_lines()
        self.assertEqual(lines, ["a", "b", "c"])
        self.assertTrue(task.result.ok)

    def test_on_done_callback(self):
        got = {}
        task = self.runner.run_async(["echo", "x"], on_done=lambda r: got.setdefault("rc", r.returncode))
        self._wait(task)
        self.assertEqual(got.get("rc"), 0)

    def test_cancel(self):
        task = self.runner.run_async(["sleep", "10"])
        time.sleep(0.1)
        task.cancel()
        self._wait(task, timeout=3.0)
        self.assertTrue(task.finished)
        self.assertTrue(task.result.cancelled)

    def test_shutdown_cancels_active(self):
        task = self.runner.run_async(["sleep", "10"])
        time.sleep(0.1)
        self.runner.shutdown()
        self._wait(task, timeout=3.0)
        self.assertTrue(task.finished)


if __name__ == "__main__":
    unittest.main()
