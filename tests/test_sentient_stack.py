import os
import unittest
from unittest.mock import patch

from sentient_stack.roma_adapter import ROMAUnavailable, is_roma_available, run_roma


class ROMAAdapterTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_roma_available())

    def test_fortytwo_key_is_not_misrepresented_as_romas_provider(self):
        with patch.dict(os.environ, {
            "PREY_ROMA_ENABLED": "true",
            "FORTYTWO_API_KEY": "test-key",
        }, clear=True):
            self.assertFalse(is_roma_available())

    def test_empty_task_is_rejected(self):
        with self.assertRaises(ValueError):
            run_roma(" ")

    def test_task_size_is_bounded(self):
        with self.assertRaises(ValueError):
            run_roma("x" * 12001)

    def test_disabled_runtime_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ROMAUnavailable):
                run_roma("test")


if __name__ == "__main__":
    unittest.main()
