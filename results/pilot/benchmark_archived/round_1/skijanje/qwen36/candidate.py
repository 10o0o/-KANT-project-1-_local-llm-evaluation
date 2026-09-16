import sys

# Li Chao Tree Implementation with Rollback
class LiChaoTree:
    def __init__(self, min_val, max_val):
        self.min_val = min_val
        self.max_val = max_val
        self.tree = [None] * (4 * (max_val - min_val + 1))
        self.history = []

    def _eval(self, line, x):
        if line is None:
            return -float('inf')
        return line[0] * x + line[1]

    def _add_line(self, node, l, r, new_line):
        mid = (l + r) // 2
        has_line = self.tree[node] is not None
        old_line = self.tree[node]
        
        # Record state for rollback
        self.history.append((node, old_line))
        
        if not has_line:
            self.tree[node] = new_line
            return

        # Determine which line is better at mid
        if self._eval(new_line, mid) > self._eval(old_line, mid):
            self.tree[node], new_line = new_line, old_line

        if l == r:
            return

        # Push the worse line to the appropriate child
        if self._eval(new_line, l) > self._eval(old_line, l):
            self._add_line(2 * node, l, mid, new_line)
        elif self._eval(new_line, r) > self._eval(old_line, r):
            self._add_line(2 * node + 1, mid + 1, r, new_line)

    def add_line(self, new_line):
        self._add_line(1, self.min_val, self.max_val, new_line)

    def rollback(self):
        if self.history:
            node, old_line = self.history.pop()
            self.tree[node] = old_line

    def query(self, x):
        res = -float('inf')
        node = 1
        l, r = self.min_val, self.max_val
        while l <= r:
            if self.tree[node] is not None:
                res = max(res, self._eval(self.tree[node], x))
            if l == r:
                break
            mid = (l + r) // 2
            if x <= mid:
                node = 2 * node
                r = mid
            else:
                node = 2 * node + 1
                l = mid + 1
        return res

def solve():
    input = sys.stdin.read
    data = input().split()
    iterator = iter(data)
    
    n = int(next(iterator))
    k = int(next(iterator))
    
    p = [0] * (n + 1)
    for i in range(2, n + 1):
        p[i] = int(next(iterator))
        
    z = [0] * (n + 1)
    for i in range(2, n + 1):
        z[i] = int(next(iterator))
        
    b = [0] * (n + 1)
    for i in range(2, n + 1):
        b[i] = int(next(iterator))
        
    # Build adjacency list
    adj = [[] for _ in range(n + 1)]
    for i in range(2, n + 1):
        adj[p[i]].append(i)
        
    # Prefix sums of b
    S = [0] * (n + 1)
    for i in range(2, n + 1):
        S[i] = S[p[i]] + b[i]
        
    lct = LiChaoTree(1, 100000)
    max_hecticness = -float('inf')
    
    # Stack for DFS: (node, depth, lines_added_count)
    # We use a deque to manage the sliding window of lines
    from collections import deque
    window_lines = deque()
    
    # Initial line for root (depth 0)
    # Root has no incoming edge, but we can treat it as a potential start point for paths
    # Actually, paths start at some node u and end at v. u can be any ancestor.
    # We add line for root: slope = -S[1] = 0, intercept = z[1]^2. But z[1] is 0.
    # So line is y = 0. It won't affect max since z >= 1.
    # We'll handle root separately or just add it.
    
    # DFS
    stack = [(1, 0)]
    while stack:
        u, depth = stack.pop()
        
        # Add line for u if u != 1 (since root has no incoming edge to form a path start)
        # Actually, a path can start at any node. The first edge is the one pointing to u.
        # So for node u, the line representing it as a start point is y = -S[u]*x + z[u]^2
        if u != 1:
            line = (-S[u], z[u] * z[u])
            lct.add_line(line)
            window_lines.append(line)
            
        # Query for current node u as endpoint
        # H = z[u]^2 + z[u]*S[u] + max(z[anc]^2 - z[u]*S[anc])
        if u != 1:
            best_anc = lct.query(z[u])
            current_h = z[u] * z[u] + z[u] * S[u] + best_anc
            if current_h > max_hecticness:
                max_hecticness = current_h
                
        # Push children to stack
        for v in adj[u]:
            stack.append((v, depth + 1))
            
        # Rollback and sliding window
        if u != 1:
            lct.rollback()
            window_lines.popleft()
            
    print(max_hecticness)

solve()