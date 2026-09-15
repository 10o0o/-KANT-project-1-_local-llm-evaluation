import sys

# Increase recursion depth for deep trees
sys.setrecursionlimit(3000)

def solve():
    # Read N
    line = sys.stdin.readline()
    if not line:
        return
    n = int(line.strip())
    
    # Read edges
    adj = [[] for _ in range(n + 1)]
    for _ in range(n - 1):
        u, v = map(int, sys.stdin.readline().split())
        adj[u].append(v)
        adj[v].append(u)
        
    # DFS to get the visit order
    visited_order = []
    visited = [False] * (n + 1)
    
    def dfs(u):
        visited[u] = True
        visited_order.append(u)
        for v in adj[u]:
            if not visited[v]:
                dfs(v)
                
    dfs(1)
    
    # The construction: p[i][j] = visited_order[(i + j - 2) % n]
    # We use 0-based indexing for the visited_order list
    # The matrix p[i][j] will be printed row by row
    
    for i in range(1, n + 1):
        row = []
        for j in range(1, n + 1):
            # The index in visited_order is (i + j - 2) % n
            idx = (i + j - 2) % n
            row.append(visited_order[idx])
        print(*(row))

if __name__ == "__main__":
    solve