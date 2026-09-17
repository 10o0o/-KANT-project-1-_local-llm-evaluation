import sys
from collections import deque

sys.setrecursionlimit(1_000_000)


def solve():
    input = sys.stdin.buffer.readline

    n, m = map(int, input().split())
    grid = [input().strip() for _ in range(n)]

    fixed_students = sum(row.count(b"2") for row in grid)
    directions = ((-1, 0), (1, 0), (0, -1), (0, 1))

    # 인접한 2가 없는 안전한 0 좌석
    safe = [[False] * m for _ in range(n)]

    for r in range(n):
        for c in range(m):
            if grid[r][c] != 48:  # '0'
                continue

            possible = True
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < m:
                    if grid[nr][nc] == 50:  # '2'
                        possible = False
                        break

            if possible:
                safe[r][c] = True

    # 체스판 색에 따른 이분 그래프 정점 번호 부여
    left_id = [[-1] * m for _ in range(n)]
    right_id = [[-1] * m for _ in range(n)]

    safe_count = 0
    left_count = 0
    right_count = 0

    for r in range(n):
        for c in range(m):
            if not safe[r][c]:
                continue

            safe_count += 1
            if (r + c) % 2 == 0:
                left_id[r][c] = left_count
                left_count += 1
            else:
                right_id[r][c] = right_count
                right_count += 1

    graph = [[] for _ in range(left_count)]

    # 왼쪽 그룹 정점의 인접 리스트 구성
    for r in range(n):
        for c in range(m):
            if not safe[r][c] or (r + c) % 2 == 1:
                continue

            u = left_id[r][c]

            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < m:
                    if safe[nr][nc]:
                        graph[u].append(right_id[nr][nc])

    pair_left = [-1] * left_count
    pair_right = [-1] * right_count

    INF = 10**9
    dist = [INF] * left_count

    def bfs():
        queue = deque()

        for u in range(left_count):
            if pair_left[u] == -1:
                dist[u] = 0
                queue.append(u)
            else:
                dist[u] = INF

        shortest = INF

        while queue:
            u = queue.popleft()

            if dist[u] >= shortest:
                continue

            current_dist = dist[u]

            for v in graph[u]:
                matched_u = pair_right[v]

                if matched_u == -1:
                    shortest = min(shortest, current_dist + 1)
                elif dist[matched_u] == INF:
                    dist[matched_u] = current_dist + 1
                    queue.append(matched_u)

        return shortest

    def dfs(u, shortest):
        current_dist = dist[u]

        for v in graph[u]:
            matched_u = pair_right[v]

            if matched_u == -1:
                if current_dist + 1 != shortest:
                    continue

                pair_left[u] = v
                pair_right[v] = u
                return True

            if dist[matched_u] == current_dist + 1:
                if dfs(matched_u, shortest):
                    pair_left[u] = v
                    pair_right[v] = u
                    return True

        dist[u] = INF
        return False

    matching = 0

    while True:
        shortest = bfs()
        if shortest == INF:
            break

        for u in range(left_count):
            if pair_left[u] == -1 and dist[u] == 0:
                if dfs(u, shortest):
                    matching += 1

    answer = fixed_students + safe_count - matching
    print(answer)


if __name__ == "__main__":
    solve()