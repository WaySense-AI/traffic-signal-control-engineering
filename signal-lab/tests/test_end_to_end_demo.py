import unittest

from examples.end_to_end_demo import build_demo_result


class EndToEndDemoTests(unittest.TestCase):
    def test_book_example_contract(self) -> None:
        result = build_demo_result()
        self.assertEqual(result["cycle"], 150)
        self.assertEqual(result["common_cycle"], 150)
        self.assertEqual(result["downstream_offset_s"], 24)
        self.assertEqual(result["stage_green_s"], {"A": 59, "B": 41, "C": 26})
        self.assertEqual(result["command_status"], "observed")


if __name__ == "__main__":
    unittest.main()
