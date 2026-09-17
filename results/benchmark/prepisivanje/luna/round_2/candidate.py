import sys
from collections import deque

sys.setrecursionlimit(1_000_000)


def maximum_matching(adjacency, right_count):
    left_count = len(adjacency)
    pair_left = [-1] * left_count
    pair_right = [-1] * right_count
    distance = [0] * left_count

    INF = 10 ** 9
    matching = 0

    while True:
        queue = deque()

        for u in range(left_count):
            if pair_left[u] == -1:
                distance[u] = 0
                queue.append(u)
            else:
                distance[u] = INF

        distance_nil = INF

        while queue:
            u = queue.popleft()

            if distance[u] >= distance_nil:
                continue

            next_distance = distance[u] + 1

            for v in adjacency[u]:
                matched_left = pair_right[v]

                if matched_left == -1:
                    if next_distance < distance_nil:
                        distance_nil = next_distance
                elif distance[matched_left] == INF:
                    distance[matched_left] = next_distance
                    queue.append(matched_left)

        if distance_nil == INF:
            return matching

        def dfs(u):
            for v in adjacency[u]:
                matched_left = pair_right[v]

                if matched_left == -1:
                    if distance[u] + 1 != distance_nil:
                        continue

                    pair_left[u] = v
                    pair_right[v] = u
                    return True

                if (
                    distance[matched_left] == distance[u] + 1
                    and dfs(matched_left)
                ):
                    pair_left[u] = v
                    pair_right[v] = u
                    return True

            distance[u] = INF
            return False

        for u in range(left_count):
            if pair_left[u] == -1 and distance[u] < distance_nil:
                if dfs(u):
                    matching += 1


def main():
    input = sys.stdin.readline

    n, m = map(int, input().split())
    grid = [list(map(int, input().strip())) for _ in range(n)]

    directions = ((1, 0), (-1, 0), (0, 1), (0, -1))

    usable = [[False] * m for _ in range(n)]
    right_id = [[-1] * m for _ in range(n)]

    left_cells = []
    right_count = 0
    fixed_students = 0

    for i in range(n):
        for j in range(m):
            value = grid[i][j]

            if value == 2:
                fixed_students += 1
            elif value == 0:
                can_use = True

                for di, dj in directions:
                    ni = i + di
                    nj = j + dj

                    if (
                        0 <= ni < n
                        and 0 <= nj < m
                        and grid[ni][nj] == 2
                    ):
                        can_use = False
                        break

                if can_use:
                    usable[i][j] = True

                    if ((i + j) & 1) == 0:
                        left_cells.append((i, j))
                    else:
                        right_id[i][j] = right_count
                        right_count += 1

    adjacency = [[] for _ in range(len(left_cells))]

    for u, (i, j) in enumerate(left_cells):
        for di, dj in directions:
            ni = i + di
            nj = j + dj

            if 0 <= ni < n and 0 <= nj < m and usable[ni][nj]:
                v = right_id[ni][nj]
                if v != -1:
                    adjacency[u].append(v)

    matching = maximum_matching(adjacency, right_count)
    usable_zero_count = len(left_cells) + right_count

    answer = fixed_students + usable_zero_count - matching
    print(answer)


if __name__ == "__main__":
    main()