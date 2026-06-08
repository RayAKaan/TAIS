"""
Spatial indexing for TAIS Swarm V6.

Replaces V5.5's O(n) resource loops with:
- Quadtree for static/semi-static resources and landmarks
- Spatial hash for dynamic agents (motes, predators)
- Combined query interface for range searches
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple, Dict, Set, Generic, TypeVar


T = TypeVar("T")


class AABB:
    """Axis-aligned bounding box."""

    def __init__(self, x: float, y: float, half_w: float, half_h: float):
        self.x = x
        self.y = y
        self.half_w = half_w
        self.half_h = half_h

    @property
    def left(self) -> float:
        return self.x - self.half_w

    @property
    def right(self) -> float:
        return self.x + self.half_w

    @property
    def top(self) -> float:
        return self.y + self.half_h

    @property
    def bottom(self) -> float:
        return self.y - self.half_h

    def contains(self, px: float, py: float) -> bool:
        return self.left <= px <= self.right and self.bottom <= py <= self.top

    def intersects(self, other: AABB) -> bool:
        return not (
            other.left > self.right or other.right < self.left
            or other.bottom > self.top or other.top < self.bottom
        )

    def distance_to(self, px: float, py: float) -> float:
        """Distance from point to closest point in AABB."""
        dx = max(self.left - px, 0, px - self.right)
        dy = max(self.bottom - py, 0, py - self.top)
        return math.sqrt(dx * dx + dy * dy)

    def expanded(self, margin: float) -> AABB:
        return AABB(self.x, self.y, self.half_w + margin, self.half_h + margin)


class QuadtreeNode(Generic[T]):
    """A node in the quadtree."""

    MAX_OBJECTS = 16
    MAX_DEPTH = 8

    def __init__(self, boundary: AABB, depth: int = 0):
        self.boundary = boundary
        self.depth = depth
        self.objects: List[Tuple[float, float, T]] = []
        self.children: Optional[List[QuadtreeNode]] = None
        self._object_count: int = 0

    def _subdivide(self):
        """Split into 4 quadrants."""
        hx = self.boundary.half_w / 2
        hy = self.boundary.half_h / 2
        cx = self.boundary.x
        cy = self.boundary.y

        self.children = [
            QuadtreeNode(AABB(cx - hx, cy + hy, hx, hy), self.depth + 1),
            QuadtreeNode(AABB(cx + hx, cy + hy, hx, hy), self.depth + 1),
            QuadtreeNode(AABB(cx - hx, cy - hy, hx, hy), self.depth + 1),
            QuadtreeNode(AABB(cx + hx, cy - hy, hx, hy), self.depth + 1),
        ]

        for x, y, obj in self.objects:
            self._insert_into_child(x, y, obj)
        self.objects = []

    def _insert_into_child(self, x: float, y: float, obj: T) -> bool:
        if self.children is None:
            return False
        for child in self.children:
            if child.boundary.contains(x, y):
                child.insert(x, y, obj)
                return True
        return False

    def insert(self, x: float, y: float, obj: T):
        if not self.boundary.contains(x, y):
            return

        self._object_count += 1

        if self.children is not None:
            if not self._insert_into_child(x, y, obj):
                self.objects.append((x, y, obj))
            return

        self.objects.append((x, y, obj))

        if len(self.objects) > self.MAX_OBJECTS and self.depth < self.MAX_DEPTH:
            self._subdivide()

    def query_range(self, range_box: AABB) -> List[Tuple[float, float, T]]:
        results: List[Tuple[float, float, T]] = []

        if not self.boundary.intersects(range_box):
            return results

        for x, y, obj in self.objects:
            if range_box.contains(x, y):
                results.append((x, y, obj))

        if self.children is not None:
            for child in self.children:
                results.extend(child.query_range(range_box))

        return results

    def query_radius(self, cx: float, cy: float, radius: float) -> List[Tuple[float, float, T, float]]:
        results: List[Tuple[float, float, T, float]] = []
        range_box = AABB(cx, cy, radius, radius)

        for x, y, obj in self.query_range(range_box):
            d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if d <= radius:
                results.append((x, y, obj, d))

        return results

    def query_k_nearest(self, cx: float, cy: float, k: int, max_radius: float = 100.0) -> List[Tuple[float, float, T, float]]:
        radius = 1.0
        while radius <= max_radius:
            results = self.query_radius(cx, cy, radius)
            if len(results) >= k:
                results.sort(key=lambda x: x[3])
                return results[:k]
            radius *= 2

        results = self.query_radius(cx, cy, max_radius)
        results.sort(key=lambda x: x[3])
        return results[:k]

    def remove(self, x: float, y: float, obj: T) -> bool:
        if not self.boundary.contains(x, y):
            return False

        for i, (ox, oy, o) in enumerate(self.objects):
            if ox == x and oy == y and o is obj:
                self.objects.pop(i)
                self._object_count -= 1
                return True

        if self.children is not None:
            for child in self.children:
                if child.remove(x, y, obj):
                    self._object_count -= 1
                    return True

        return False

    def update_position(self, old_x: float, old_y: float, new_x: float, new_y: float, obj: T) -> bool:
        if self.boundary.contains(new_x, new_y):
            if self.children is not None:
                for child in self.children:
                    if child.boundary.contains(new_x, new_y):
                        if child.remove(old_x, old_y, obj):
                            child.insert(new_x, new_y, obj)
                            return True
                for i, (ox, oy, o) in enumerate(self.objects):
                    if ox == old_x and oy == old_y and o is obj:
                        self.objects[i] = (new_x, new_y, obj)
                        return True
            else:
                for i, (ox, oy, o) in enumerate(self.objects):
                    if ox == old_x and oy == old_y and o is obj:
                        self.objects[i] = (new_x, new_y, obj)
                        return True
        else:
            if self.remove(old_x, old_y, obj):
                return False
        return False

    def __len__(self) -> int:
        return self._object_count


class SpatialHash(Generic[T]):
    """Spatial hash for fast-moving objects (motes, predators)."""

    def __init__(self, cell_size: float, world_size: float):
        self.cell_size = cell_size
        self.world_size = world_size
        self.cells: Dict[Tuple[int, int], Set[Tuple[int, T]]] = {}
        self.positions: Dict[int, Tuple[float, float]] = {}

    def _cell(self, x: float, y: float) -> Tuple[int, int]:
        return (int(x // self.cell_size), int(y // self.cell_size))

    def insert(self, obj_id: int, x: float, y: float, obj: T):
        cell = self._cell(x, y)

        if obj_id in self.positions:
            old_cell = self._cell(*self.positions[obj_id])
            if old_cell in self.cells:
                self.cells[old_cell].discard((obj_id, obj))

        if cell not in self.cells:
            self.cells[cell] = set()
        self.cells[cell].add((obj_id, obj))
        self.positions[obj_id] = (x, y)

    def remove(self, obj_id: int) -> Optional[T]:
        if obj_id not in self.positions:
            return None
        old_cell = self._cell(*self.positions[obj_id])
        if old_cell in self.cells:
            for oid, obj in list(self.cells[old_cell]):
                if oid == obj_id:
                    self.cells[old_cell].discard((oid, obj))
                    del self.positions[obj_id]
                    return obj
        return None

    def query_radius(self, cx: float, cy: float, radius: float, exclude_id: Optional[int] = None) -> List[Tuple[T, float]]:
        results: List[Tuple[T, float]] = []
        cell_radius = int(math.ceil(radius / self.cell_size))
        center_cell = self._cell(cx, cy)

        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                cell = (center_cell[0] + dx, center_cell[1] + dy)
                if cell not in self.cells:
                    continue
                for obj_id, obj in self.cells[cell]:
                    if exclude_id is not None and obj_id == exclude_id:
                        continue
                    px, py = self.positions[obj_id]
                    d = math.sqrt((px - cx) ** 2 + (py - cy) ** 2)
                    if d <= radius:
                        results.append((obj, d))

        return results

    def query_k_nearest(self, cx: float, cy: float, k: int, max_radius: float = 100.0, exclude_id: Optional[int] = None) -> List[Tuple[T, float]]:
        radius = self.cell_size
        while radius <= max_radius:
            results = self.query_radius(cx, cy, radius, exclude_id)
            if len(results) >= k:
                results.sort(key=lambda x: x[1])
                return results[:k]
            radius *= 2

        results = self.query_radius(cx, cy, max_radius, exclude_id)
        results.sort(key=lambda x: x[1])
        return results[:k]

    def __len__(self) -> int:
        return len(self.positions)


class UnifiedSpatialIndex(Generic[T]):
    """Combined interface: Quadtree for resources, SpatialHash for agents."""

    def __init__(self, world_size: float, hash_cell_size: float = 4.0):
        self.world_size = world_size
        self.resource_tree: QuadtreeNode[T] = QuadtreeNode(
            AABB(world_size / 2, world_size / 2, world_size / 2, world_size / 2)
        )
        self.agent_hash: SpatialHash[T] = SpatialHash(hash_cell_size, world_size)

    def insert_resource(self, x: float, y: float, resource: T):
        self.resource_tree.insert(x, y, resource)

    def insert_agent(self, agent_id: int, x: float, y: float, agent: T):
        self.agent_hash.insert(agent_id, x, y, agent)

    def update_agent(self, agent_id: int, new_x: float, new_y: float, agent: T):
        self.agent_hash.insert(agent_id, new_x, new_y, agent)

    def remove_agent(self, agent_id: int) -> Optional[T]:
        return self.agent_hash.remove(agent_id)

    def query_resources(self, cx: float, cy: float, radius: float) -> List[Tuple[float, float, T, float]]:
        return self.resource_tree.query_radius(cx, cy, radius)

    def query_agents(self, cx: float, cy: float, radius: float, exclude_id: Optional[int] = None) -> List[Tuple[T, float]]:
        return self.agent_hash.query_radius(cx, cy, radius, exclude_id)

    def query_all(self, cx: float, cy: float, radius: float, exclude_id: Optional[int] = None) -> Tuple[List[Tuple[float, float, T, float]], List[Tuple[T, float]]]:
        return (
            self.query_resources(cx, cy, radius),
            self.query_agents(cx, cy, radius, exclude_id)
        )
