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


class TestSolutionLength(unittest.TestCase):
    def test_min_solution_length_formula(self):
        self.assertEqual(gm.MIN_PATH_FACTOR, 0.5)
        self.assertEqual(gm.min_solution_length(10), 50)
        self.assertEqual(gm.min_solution_length(20), 200)
        self.assertEqual(gm.min_solution_length(7), 25)

    def test_solution_meets_minimum(self):
        for n in (4, 6, 8, 10, 12, 16, 20):
            target = gm.min_solution_length(n)
            for s in range(8):
                rng = random.Random(1000 * n + s)
                right, down, entrance, exit_, length = gm.generate_long_maze(n, rng)
                start = gm.opening_to_cell(entrance, n, n)
                goal = gm.opening_to_cell(exit_, n, n)
                path = gm.find_path(right, down, n, n, start, goal)
                self.assertIsNotNone(path)
                self.assertEqual(len(path), length)
                self.assertGreaterEqual(len(path), target)

    def test_entrance_and_exit_are_far_apart(self):
        for n in (8, 12, 20):
            rng = random.Random(n)
            _, _, entrance, exit_, _ = gm.generate_long_maze(n, rng)
            self.assertNotEqual(entrance, exit_)
            start = gm.opening_to_cell(entrance, n, n)
            goal = gm.opening_to_cell(exit_, n, n)
            self.assertGreater(abs(start[0] - goal[0]) + abs(start[1] - goal[1]), n // 2)

    def test_cell_to_opening_inverts_opening_to_cell(self):
        n = 10
        for spec in [("top", 0), ("top", 9), ("bottom", 4), ("left", 5), ("right", 7)]:
            cell = gm.opening_to_cell(spec, n, n)
            self.assertEqual(gm.cell_to_opening(cell, n, n), spec)


class TestMazeComplexity(unittest.TestCase):
    def test_has_dead_ends_and_junctions(self):
        for n in (6, 10, 16, 20):
            for s in range(6):
                rng = random.Random(7000 * n + s)
                right, down, *_ = gm.generate_long_maze(n, rng)
                dead, junc = gm.count_dead_ends_and_junctions(right, down, n, n)
                self.assertGreaterEqual(dead, max(2, n // 3))
                self.assertGreaterEqual(junc, max(1, n // 6))

    def test_perfect_maze_still_holds(self):
        for n in (6, 10, 16):
            rng = random.Random(n + 1)
            right, down, *_ = gm.generate_long_maze(n, rng)
            self.assertEqual(gm.count_open_passages(right, down), n * n - 1)


class TestDifficultySizing(unittest.TestCase):
    def test_sizes_are_non_decreasing(self):
        sizes = gm.grid_sizes(20, gm.DEFAULT_DIFFICULTY)
        for a, b in zip(sizes, sizes[1:]):
            self.assertLessEqual(a, b)

    def test_first_smaller_than_last(self):
        sizes = gm.grid_sizes(20, gm.DEFAULT_DIFFICULTY)
        self.assertLess(sizes[0], sizes[-1])

    def test_average_increases_with_difficulty(self):
        avg = [sum(gm.grid_sizes(20, d)) / 20 for d in (1.0, 2.0, 3.0, 4.0)]
        for a, b in zip(avg, avg[1:]):
            self.assertLess(a, b)

    def test_sizes_respect_bounds(self):
        for d in (0.0, 1.0, 3.0, 10.0):
            for s in gm.grid_sizes(20, d):
                self.assertGreaterEqual(s, 4)
                self.assertLessEqual(s, gm.MAX_GRID)

    def test_count_matches_pages(self):
        self.assertEqual(len(gm.grid_sizes(30, gm.DEFAULT_DIFFICULTY)), 30)


class TestRandomnessAndReproducibility(unittest.TestCase):
    def test_same_seed_same_maze(self):
        a = carve(15, 15, seed=123)
        b = carve(15, 15, seed=123)
        self.assertEqual(a, b)

    def test_different_seeds_differ(self):
        a = carve(15, 15, seed=1)
        b = carve(15, 15, seed=2)
        self.assertNotEqual(a, b)

    def test_openings_reproducible(self):
        self.assertEqual(gm.choose_openings(10, random.Random(7)),
                         gm.choose_openings(10, random.Random(7)))

