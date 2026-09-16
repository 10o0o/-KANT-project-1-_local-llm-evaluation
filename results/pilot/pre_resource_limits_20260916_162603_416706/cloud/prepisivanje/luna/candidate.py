import sys
from collections import deque


def main():
    input = sys.stdin.readline

    n, m = map(int, input().split())
    grid = [input().strip() for _ in range(n)]

    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    fixed_students = 0
    eligible = [[False] * m for _ in range(n)]
    eligible_count = 0

    for r in range(n):
        for c in range(m):
            if grid[r][c] == '2':
                fixed_students += 1
            elif grid[r][c] == '0':
                can_use = True

                for dr, dc in directions:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < n and 0 <= nc < m:
                        if grid[nr][nc] == '2':
                            can_use = False
                            break

                if can_use:
                    eligible[r][c] = True
                    eligible_count += 1

    total_cells = n * m
    adjacency = [[] for _ in range(total_cells)]
    left_vertices = []

    for r in range(n):
        for c in range(m):
            if not eligible[r][c]:
                continue
            if (r + c) % 2 != 0:
                continue

            u = r * m + c
            left_vertices.append(u)

            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < m:
                    if eligible[nr][nc]:
                        v = nr * m + nc
                        adjacency[u].append(v)

    pair_left = [-1] * total_cells
    pair_right = [-1] * total_cells
    distance = [0] * total_cells
    infinity = 10**9

    sys.setrecursionlimit(max(10000, total_cells * 2 + 100))

    def bfs():
        queue = deque()

        for u in left_vertices:
            if pair_left[u] == -1:
                distance[u] = 0
                queue.append(u)
            else:
                distance[u] = infinity

        shortest = infinity

        while queue:
            u = queue.popleft()

            if distance[u] >= shortest:
                continue

            for v in adjacency[u]:
                matched_left = pair_right[v]

                if matched_left == -1:
                    shortest = distance[u] + 1
                elif distance[matched_left] == infinity:
                    distance[matched_left] = distance[u] + 1
                    queue.append(matched_left)

        return shortest

    def dfs(u, shortest):
        for v in adjacency[u]:
            matched_left = pair_right[v]

            if matched_left == -1:
                if distance[u] + 1 == shortest:
                    pair_left[u] = v
                    pair_right[v] = u
                    return True
            elif (
                distance[matched_left] == distance[u] + 1
                and dfs(matched_left, shortest)
            ):
                pair_left[u] = v
                pair_right[v] = u
                return True

        distance[u] = infinity
        return False

    matching = 0

    while True:
        shortest = bfs()
        if shortest == infinity:
            break

        for u in left_vertices:
            if pair_left[u] == -1 and dfs(u, shortest):
                matching += 1

    answer = fixed_students + eligible_count - matching
    print(answer)


if __name__ == "__main__":
    main()