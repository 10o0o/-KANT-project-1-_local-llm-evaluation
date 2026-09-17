import sys
from bisect import bisect_right

sys.setrecursionlimit(3000)

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    it = iter(input_data)
    n = int(next(it))
    m = int(next(it))
    k = int(next(it))
    h = [int(next(it)) for _ in range(k)]
    h.sort()

    grid = []
    for _ in range(n):
        grid.append([int(next(it)) for _ in range(m)])

    size = k
    tree = [0] * (2 * size)
    lazy = [0] * (2 * size)

    def push(i):
        if lazy[i]:
            lazy[2 * i] += lazy[i]
            tree[2 * i] += lazy[i]
            lazy[2 * i + 1] += lazy[i]
            tree[2 * i + 1] += lazy[i]
            lazy[i] = 0

    def update(node, start, end, l, r, val):
        if l > end or r < start:
            return
        if l <= start and end <= r:
            tree[node] += val
            lazy[node] += val
            return
        push(node)
        mid = (start + end) // 2
        update(2 * node, start, mid, l, r, val)
        update(2 * node + 1, mid + 1, end, l, r, val)
        tree[node] = max(tree[2 * node], tree[2 * node + 1])

    ans = 0
    col_max = [0] * m

    for i in range(n):
        # Reset segment tree to initial state: tree[j] = j+1
        for j in range(size):
            tree[size + j] = j + 1
            lazy[size + j] = 0
        for j in range(size - 1, 0, -1):
            tree[j] = max(tree[2 * j], tree[2 * j + 1])
            lazy[j] = 0

        idxs = [0] * m
        empty_cnt = 0
        for c in range(m):
            if grid[i][c] == 0:
                idxs[c] = bisect_right(h, col_max[c])
                empty_cnt += 1

        # Initialize first window
        for c in range(k):
            if idxs[c] > 0:
                update(1, 0, size - 1, 0, idxs[c] - 1, 1)

        if empty_cnt == k and tree[1] <= k:
            ans += 1

        # Slide window
        for c in range(k, m):
            out_c = c - k
            if idxs[out_c] > 0:
                update(1, 0, size - 1, 0, idxs[out_c] - 1, -1)
            if grid[i][out_c] == 0:
                empty_cnt -= 1

            if idxs[c] > 0:
                update(1, 0, size - 1, 0, idxs[c] - 1, 1)
            if grid[i][c] == 0:
                empty_cnt += 1

            if empty_cnt == k and tree[1] <= k:
                ans += 1

        # Update column maximums for the next row
        for c in range(m):
            if grid[i][c] > col_max[c]:
                col_max[c] = grid[i][c]

    print(ans)

if __name__ == '__main__':
    solve()