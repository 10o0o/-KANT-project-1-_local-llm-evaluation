import sys

def solve():
    input = sys.stdin.read
    data = input().split()
    idx = 0
    N = int(data[idx]); idx += 1
    adj = [[] for _ in range(N + 1)]
    for _ in range(N - 1):
        u = int(data[idx]); idx += 1
        v = int(data[idx]); idx += 1
        adj[u].append(v)
        adj[v].append(u)

    # Root the tree at vertex 1
    parent = [0] * (N + 1)
    order = []
    stack = [1]
    visited = [False] * (N + 1)
    visited[1] = True
    while stack:
        u = stack.pop()
        order.append(u)
        for v in adj[u]:
            if not visited[v]:
                visited[v] = True
                parent[v] = u
                stack.append(v)

    # For each vertex i from 1 to N, output the DFS order starting from i
    # We can generate this by rotating the base DFS order and adjusting parent pointers
    # Actually, a simpler way: for each root r, do a DFS/BFS traversal.
    # But doing N DFS runs is O(N^2), which is fine for N=2000.
    
    out = []
    for r in range(1, N + 1):
        # DFS from r
        res = []
        stack = [r]
        vis = [False] * (N + 1)
        vis[r] = True
        while stack:
            u = stack.pop()
            res.append(u)
            # Push neighbors in reverse order to maintain consistent traversal
            # Order of children doesn't strictly matter for correctness, 
            # but we must ensure we traverse the whole tree.
            for v in adj[u]:
                if not vis[v]:
                    vis[v] = True
                    stack.append(v)
        out.append(' '.join(map(str, res)))
    
    sys.stdout.write('\n'.join(out) + '\n')

solve()