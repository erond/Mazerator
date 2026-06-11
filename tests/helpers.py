import random

from maze_generator import generate_mazes as gm


def carve(cols, rows, seed):
    return gm.generate_maze(cols, rows, random.Random(seed))

