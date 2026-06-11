from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import random
import unittest

from maze_generator import generate_mazes as gm
from tests.helpers import carve


class TestMazeStructure(unittest.TestCase):
    def test_dimensions(self):
        right, down = carve(7, 5, seed=1)
        self.assertEqual(len(right), 5)
        self.assertEqual(len(down), 5)
        for row in right + down:
            self.assertEqual(len(row), 7)

    def test_perfect_maze_is_a_spanning_tree(self):
        for n in (4, 8, 12, 20):
            right, down = carve(n, n, seed=n)
            self.assertEqual(gm.count_open_passages(right, down), n * n - 1)

    def test_all_cells_reachable(self):
        n = 10
        right, down = carve(n, n, seed=42)
        reached = 0
        for r in range(n):
            for col in range(n):
                if gm.find_path(right, down, n, n, (0, 0), (r, col)) is not None:
                    reached += 1
        self.assertEqual(reached, n * n)


class TestSolvability(unittest.TestCase):
    def test_entrance_to_exit_path_exists(self):
        n = 12
        for s in range(50):
            rng = random.Random(s)
            entrance, exit_ = gm.choose_openings(n, rng)
            right, down = gm.generate_maze(n, n, rng)
            start = gm.opening_to_cell(entrance, n, n)
            goal = gm.opening_to_cell(exit_, n, n)
            path = gm.find_path(right, down, n, n, start, goal)
            self.assertIsNotNone(path)
            self.assertEqual(path[0], start)
            self.assertEqual(path[-1], goal)


class TestOpenings(unittest.TestCase):
    def test_edges_and_ranges(self):
        n = 9
        for s in range(100):
            entrance, exit_ = gm.choose_openings(n, random.Random(s))
            self.assertIn(entrance[0], ("top", "left"))
            self.assertIn(exit_[0], ("bottom", "right"))
            self.assertTrue(0 <= entrance[1] < n)
            self.assertTrue(0 <= exit_[1] < n)

    def test_opening_to_cell_corners(self):
        self.assertEqual(gm.opening_to_cell(("top", 3), 10, 10), (0, 3))
        self.assertEqual(gm.opening_to_cell(("bottom", 3), 10, 10), (9, 3))
        self.assertEqual(gm.opening_to_cell(("left", 4), 10, 10), (4, 0))
        self.assertEqual(gm.opening_to_cell(("right", 4), 10, 10), (4, 9))

