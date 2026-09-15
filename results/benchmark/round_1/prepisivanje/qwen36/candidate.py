import sys
from collections import deque

def solve():
    input = sys.stdin.read
    data = input().split()
    if not data:
        return
    
    n, m = int(data[0]), int(data[1])
    grid = data[2:2+n]
    
    fixed_students = 0
    valid_seats = []
    seat_to_idx = {}
    
    # Directions for neighbors
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    
    # Identify valid empty seats (0s not adjacent to any 2)
    for r in range(n):
        for c in range(m):
            if grid[r][c] == '2':
                fixed_students += 1
            elif grid[r][c] == '0':
                is_valid = True
                for dr, dc in dirs:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < n and 0 <= nc < m:
                        if grid[nr][nc] == '2':
                            is_valid = False
                            break
                if is_valid:
                    idx = len(valid_seats)
                    valid_seats.append((r, c))
                    seat_to_idx[(r, c)] = idx
                    
    num_valid = len(valid_seats)
    if num_valid == 0:
        print(fixed_students)
        return
        
    # Build adjacency list for bipartite graph
    adj = [[] for _ in range(num_valid)]
    for i, (r, c) in enumerate(valid_seats):
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if (nr, nc) in seat_to_idx:
                j = seat_to_idx[(nr, nc)]
                adj[i].append(j)
                
    # Hopcroft-Karp Algorithm for Maximum Bipartite Matching
    # Partition vertices based on (r+c) % 2
    U = [i for i, (r, c) in enumerate(valid_seats) if (r + c) % 2 == 0]
    V = [i for i, (r, c) in enumerate(valid_seats) if (r + c) % 2 == 1]
    
    pair_u = [-1] * num_valid
    pair_v = [-1] * num_valid
    dist = [-1] * num_valid
    
    def bfs():
        queue = deque()
        for u in U:
            if pair_u[u] == -1:
                dist[u] = 0
                queue.append(u)
            else:
                dist[u] = float('inf')
        dist[-1] = float('inf')
        
        while queue:
            u = queue.popleft()
            if dist[u] < dist[-1]:
                for v in adj[u]:
                    if pair_v[v] == -1:
                        if dist[pair_v[v]] == float('inf'):
                            dist[pair_v[v]] = dist[u] + 1
                            queue.append(pair_v[v])
                    else:
                        if dist[pair_v[v]] == float('inf'):
                            dist[pair_v[v]] = dist[u] + 1
                            queue.append(pair_v[v])
        return dist[-1] != float('inf')
    
    def dfs(u):
        if u != -1:
            for v in adj[u]:
                if dist[pair_v[v]] == dist[u] + 1:
                    if dfs(pair_v[v]):
                        pair_v[v] = u
                        pair_u[u] = v
                        return True
            dist[u] = float('inf')
            return False
        return True
        
    matching = 0
    while bfs():
        for u in U:
            if pair_u[u] == -1:
                if dfs(u):
                    matching += 1
                    
    max_mischievous = num_valid - matching
    print(fixed_students + max_mischievous)

if __name__ == '__main__':
    solve()