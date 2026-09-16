import sys

sys.setrecursionlimit(20000)

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return

    n, m = int(input_data[0]), int(input_data[1])
    grid = input_data[2:]

    fixed_count = 0
    available = []
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    # 1. '2'와 인접하지 않은 '0' 좌석만 사용 가능
    for r in range(n):
        for c in range(m):
            cell = grid[r][c]
            if cell == '2':
                fixed_count += 1
            elif cell == '0':
                adj_to_2 = False
                for dr, dc in dirs:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < n and 0 <= nc < m and grid[nr][nc] == '2':
                        adj_to_2 = True
                        break
                if not adj_to_2:
                    available.append((r, c))

    # 좌표를 인덱스로 매핑
    pos_to_idx = {pos: i for i, pos in enumerate(available)}
    left_nodes = []
    adj = [[] for _ in range(len(available))]

    # 2. 이분 그래프 구성 (격자는 r+c의 홀짝성에 따라 이분됨)
    for r, c in available:
        idx = pos_to_idx[(r, c)]
        if (r + c) % 2 == 0:
            left_nodes.append(idx)
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < m and (nr, nc) in pos_to_idx:
                    adj[idx].append(pos_to_idx[(nr, nc)])

    # 3. DFS 기반 최대 이분 매칭 (Kuhn's Algorithm)
    match_right = [-1] * len(available)
    vis = [0] * len(available)
    vis_token = 0

    def dfs(u):
        for v in adj[u]:
            if vis[v] != vis_token:
                vis[v] = vis_token
                if match_right[v] == -1 or dfs(match_right[v]):
                    match_right[v] = u
                    return True
        return False

    matching_size = 0
    for u in left_nodes:
        vis_token += 1
        if dfs(u):
            matching_size += 1

    # 이분 그래프에서 최대 독립 집합 크기 = 정점 수 - 최대 매칭 크기
    ans = fixed_count + len(available) - matching_size
    print(ans)

if __name__ == '__main__':
    solve()