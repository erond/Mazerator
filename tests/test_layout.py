from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import math
import unittest

from maze_generator import generate_mazes as gm


class TestLayoutGeometry(unittest.TestCase):
    @staticmethod
    def _point_to_segment_distance(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = ((px - x1) * dx + (py - y1) * dy) / float(dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        qx, qy = x1 + t * dx, y1 + t * dy
        return math.hypot(px - qx, py - qy)

    def test_icon_never_overlaps_arrow(self):
        points = [
            (200.0, 300.0, "top"),
            (200.0, 300.0, "bottom"),
            (200.0, 300.0, "left"),
            (200.0, 300.0, "right"),
            (20.0, 300.0, "left"),
            (gm.PAGE_W - 20.0, 300.0, "right"),
            (120.0, gm.PAGE_H - 20.0, "top"),
            (120.0, 20.0, "bottom"),
        ]
        icons = ("bunny", "balloon", "cat", "castle")
        clearance = 8.0
        for point in points:
            for size in (17, 19):
                for icon_name in icons:
                    cx, cy = gm.icon_center_for_opening(point, icon_name, size)
                    radius = gm.icon_collision_radius(icon_name, size)
                    x1, y1, x2, y2 = gm.arrow_for_opening(point, True)
                    d = self._point_to_segment_distance(cx, cy, x1, y1, x2, y2)
                    self.assertGreater(d, radius + clearance - 0.1)

    def test_icon_never_truncated_by_page_border(self):
        points = [
            (10.0, gm.PAGE_H - 10.0, "top"),
            (gm.PAGE_W - 10.0, gm.PAGE_H - 10.0, "top"),
            (10.0, 10.0, "bottom"),
            (gm.PAGE_W - 10.0, 10.0, "bottom"),
            (10.0, gm.PAGE_H / 2, "left"),
            (gm.PAGE_W - 10.0, gm.PAGE_H / 2, "right"),
        ]
        for point in points:
            for size in (17, 19):
                for icon_name in ("bunny", "balloon", "cat", "castle"):
                    cx, cy = gm.icon_center_for_opening(point, icon_name, size)
                    left, right, down, up = gm.icon_extents(icon_name, size)
                    self.assertGreaterEqual(cx - left, 0.0)
                    self.assertLessEqual(cx + right, gm.PAGE_W)
                    self.assertGreaterEqual(cy - down, 0.0)
                    self.assertLessEqual(cy + up, gm.PAGE_H)

    def test_label_never_overlaps_arrow_icon_or_maze(self):
        labels = ("START", "PARTENZA")
        points = [
            (10.0, gm.PAGE_H - 10.0, "top"),
            (gm.PAGE_W - 10.0, gm.PAGE_H - 10.0, "top"),
            (10.0, 10.0, "bottom"),
            (gm.PAGE_W - 10.0, 10.0, "bottom"),
            (10.0, gm.PAGE_H / 2, "left"),
            (gm.PAGE_W - 10.0, gm.PAGE_H / 2, "right"),
            (gm.MAZE_X0, gm.MAZE_Y0 + gm.MAZE_SIDE * 0.9, "left"),
            (gm.MAZE_X0 + gm.MAZE_SIDE, gm.MAZE_Y0 + gm.MAZE_SIDE * 0.1, "right"),
        ]
        maze_rect = (gm.MAZE_X0, gm.MAZE_Y0, gm.MAZE_X0 + gm.MAZE_SIDE, gm.MAZE_Y0 + gm.MAZE_SIDE)
        for point in points:
            for icon_name, size in (("bunny", 17), ("castle", 19)):
                cx, cy = gm.icon_center_for_opening(point, icon_name, size)
                left, right, down, up = gm.icon_extents(icon_name, size)
                icon_rect = (cx - left, cy - down, cx + right, cy + up)
                arrow = gm.arrow_for_opening(point, point[2] in {"top", "left"})
                for text in labels:
                    lx, ly = gm.label_placement_for_opening(point, (cx, cy), icon_name, size, text, 7.5)
                    label_rect = gm._rect_for_center(lx, ly, text, 7.5)
                    self.assertFalse(gm._rects_overlap(label_rect, icon_rect))
                    self.assertFalse(gm._rects_overlap(label_rect, maze_rect))
                    self.assertGreaterEqual(gm._rect_segment_distance(label_rect, arrow), 3.0)
                    self.assertGreaterEqual(label_rect[0], 0.0)
                    self.assertLessEqual(label_rect[2], gm.PAGE_W)
                    self.assertGreaterEqual(label_rect[1], 0.0)
                    self.assertLessEqual(label_rect[3], gm.PAGE_H)

    def test_motif_conflicts_with_opening_decorations(self):
        point = (60.0, gm.PAGE_H - 40.0, "top")
        icon_name = "castle"
        size = 19
        cx, cy = gm.icon_center_for_opening(point, icon_name, size)
        icon_radius = gm.icon_collision_radius(icon_name, size)
        lx, ly = gm.label_placement_for_opening(point, (cx, cy), icon_name, size, "START", 7.5)
        label_rect = gm._rect_for_center(lx, ly, "START", 7.5)
        protected_circles = [(cx, cy, icon_radius)]
        protected_rects = [label_rect]

        # Motif near icon must be rejected.
        self.assertTrue(
            gm._motif_conflicts(
                cx + 5, cy + 5, 10, point, (gm.PAGE_W - 60.0, 80.0, "right"),
                protected_circles, protected_rects
            )
        )
        # Motif near label must be rejected.
        self.assertTrue(
            gm._motif_conflicts(
                lx, ly, 8, point, (gm.PAGE_W - 60.0, 80.0, "right"),
                protected_circles, protected_rects
            )
        )

