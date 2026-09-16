import sys
from collections import deque

sys.setrecursionlimit(1_000_000)


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return

    n = int(data[0])
    m = int(data[1])
    grid = [data[2 + i].decode() for i in range(n)]

    good_count = sum(row.count("2") for row in grid)
    directions = ((-1, 0), (1, 0), (0, -1), (0, 1))

    usable = [[False] * m for _ in range(n)]

    for i in range(n):
        for j in range(m):
            if grid[i][j] != "0":
                continue

            if (
                (i > 0 and grid[i - 1][j] == "2")
                or (i + 1 < n and grid[i + 1][j] == "2")
                or (j > 0 and grid[i][j - 1] == "2")
                or (j + 1 < m and grid[i][j + 1] == "2")
            ):
                continue

            usable[i][j] = True

    left_id = [[-1] * m for _ in range(n)]
    right_id = [[-1] * m for _ in range(n)]

    left_count = 0
    right_count = 0

    for i in range(n):
        for j in range(m):
            if not usable[i][j]:
                continue

            if ((i + j) & 1) == 0:
                left_id[i][j] = left_count
                left_count += 1
            else:
                right_id[i][j] = right_count
                right_count += 1

    adjacency = [[] for _ in range(left_count)]

    for i in range(n):
        for j in range(m):
            u = left_id[i][j]
            if u == -1:
                continue

            for di, dj in directions:
                ni = i + di
                nj = j + dj

                if 0 <= ni < n and 0 <= nj < m:
                    v = right_id[ni][nj]
                    if v != -1:
                        adjacency[u].append(v)

    pair_left = [-1] * left_count
    pair_right = [-1] * right_count
    distance = [0] * left_count
    INF = 10**9

    def bfs():
        queue = deque()

        for u in range(left_count):
            if pair_left[u] == -1:
                distance[u] = 0
                queue.append(u)
            else:
                distance[u] = INF

        shortest = INF

        while queue:
            u = queue.popleft()

            if distance[u] >= shortest:
                continue

            next_distance = distance[u] + 1

            for v in adjacency[u]:
                matched_u = pair_right[v]

                if matched_u == -1:
                    if next_distance < shortest:
                        shortest = next_distance
                elif distance[matched_u] == INF:
                    distance[matched_u] = next_distance
                    queue.append(matched_u)

        return shortest

    def dfs(u, shortest):
        current_distance = distance[u]

        for v in adjacency[u]:
            matched_u = pair_right[v]

            if matched_u == -1:
                if current_distance + 1 != shortest:
                    continue

                pair_left[u] = v
                pair_right[v] = u
                return True

            if (
                distance[matched_u] == current_distance + 1
                and dfs(matched_u, shortest)
            ):
                pair_left[u] = v
                pair_right[v] = u
                return True

        distance[u] = INF
        return False

    matching = 0

    while True:
        shortest = bfs()
        if shortest == INF:
            break

        for u in range(left_count):
            if pair_left[u] == -1 and distance[u] != INF:
                if dfs(u, shortest):
                    matching += 1

    usable_count = left_count + right_count
    answer = good_count + usable_count - matching
    print(answer)


if __name__ == "__main__":
    main()