import sys

sys.setrecursionlimit(20000)

def solve():
    data = sys.stdin.read().split()
    if not data:
        return
    n, m = map(int, data[:2])
    grid = data[2:2+n]

    fixed_count = 0
    pos_to_idx = {}
    idx = 0
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    for r in range(n):
        for c in range(m):
            cell = grid[r][c]
            if cell == '2':
                fixed_count += 1
            elif cell == '0':
                has_adj_2 = False
                for dr, dc in dirs:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < n and 0 <= nc < m and grid[nr][nc] == '2':
                        has_adj_2 = True
                        break
                if not has_adj_2:
                    pos_to_idx[(r, c)] = idx
                    idx += 1

    num_avail = idx
    adj = [[] for _ in range(num_avail)]
    for (r, c), i in pos_to_idx.items():
        if (r + c) % 2 == 0:
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if (nr, nc) in pos_to_idx:
                    adj[i].append(pos_to_idx[(nr, nc)])

    match = [-1] * num_avail
    vis = [0] * num_avail
    vis_token = 0

    def dfs(u):
        for v in adj[u]:
            if vis[v] != vis_token:
                vis[v] = vis_token
                if match[v] == -1 or dfs(match[v]):
                    match[v] = u
                    return True
        return False

    matching_size = 0
    for i in range(num_avail):
        vis_token += 1
        if dfs(i):
            matching_size += 1

    print(fixed_count + num_avail - matching_size)

if __name__ == '__main__':
    solve()