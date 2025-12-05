# trendengine/engine.py
import math
from typing import List, Tuple, Dict, Optional

# Haversine distance (km)
def haversine(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    R = 6371  # Earth radius km
    dlat = math.radians(b_lat - a_lat)
    dlon = math.radians(b_lon - a_lon)
    alat = math.radians(a_lat)
    blat = math.radians(b_lat)
    aa = math.sin(dlat / 2) ** 2 + math.cos(alat) * math.cos(blat) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(aa), math.sqrt(1 - aa))
    return R * c

# Create distance matrix
def build_distance_matrix(points: List[Tuple[float, float]]) -> List[List[float]]:
    n = len(points)
    mat = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine(points[i][0], points[i][1], points[j][0], points[j][1])
            mat[i][j] = d
            mat[j][i] = d
    return mat

# Nearest neighbour heuristic
def nearest_neighbor_order(distance_matrix: List[List[float]], start: int = 0) -> List[int]:
    n = len(distance_matrix)
    if n == 0:
        return []
    visited = [False] * n
    order = [start]
    visited[start] = True
    current = start
    for _ in range(n - 1):
        next_node = None
        best_d = float("inf")
        for j in range(n):
            if not visited[j] and distance_matrix[current][j] < best_d:
                best_d = distance_matrix[current][j]
                next_node = j
        if next_node is None:
            break
        order.append(next_node)
        visited[next_node] = True
        current = next_node
    return order

# 2-opt improvement
def two_opt(order: List[int], distance_matrix: List[List[float]]) -> List[int]:
    n = len(order)
    if n < 4:
        return order
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                a, b = order[i - 1], order[i]
                c, d = order[j], order[j + 1]
                # current edges: (a-b) + (c-d)
                # new edges after swap: (a-c) + (b-d)
                if distance_matrix[a][c] + distance_matrix[b][d] < distance_matrix[a][b] + distance_matrix[c][d]:
                    # perform 2-opt (reverse segment i..j)
                    order[i:j + 1] = reversed(order[i:j + 1])
                    improved = True
        # loop until no improvement
    return order

# Compute total distance of an order
def total_distance(order: List[int], distance_matrix: List[List[float]]) -> float:
    if not order:
        return 0.0
    dist = 0.0
    for i in range(len(order) - 1):
        dist += distance_matrix[order[i]][order[i + 1]]
    return dist

# High level: compute optimized order and return indexes + total distance
def optimize_route(points: List[Tuple[float, float]], start_index: int = 0) -> Dict:
    """
    points: list of (lat, lon)
    start_index: integer index in points list to start from (default 0)
    returns: dict { "order": [idx,...], "optimized_order": [idx,...], "total_distance_km": float }
    """
    if not points:
        return {"order": [], "optimized_order": [], "total_distance_km": 0.0}

    dm = build_distance_matrix(points)
    initial = nearest_neighbor_order(dm, start=start_index)
    improved = two_opt(initial.copy(), dm)
    dist = total_distance(improved, dm)
    return {"order": initial, "optimized_order": improved, "total_distance_km": round(dist, 3)}
