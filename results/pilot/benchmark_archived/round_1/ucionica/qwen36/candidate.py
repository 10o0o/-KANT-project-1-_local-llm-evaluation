import sys
from bisect import bisect_right

sys.setrecursionlimit(10000)

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
    grid = [[int(next(it)) for _ in range(m)] for _ in range(n)]

    col_max = [0] * m
    size = 1
    while size < k:
        size *= 2
    
    tree = [0] * (2 * size)
    lazy = [0] * (2 * size)

    # 초기값 설정: T_i = i - (k - 1)
    for i in range(k):
        tree[size + i] = i - (k - 1)
    for i in range(size - 1, 0, -1):
        tree[i] = max(tree[2 * i], tree[2 * i + 1])

    def push(node):
        if lazy[node]:
            for child in (2 * node, 2 * node + 1):
                tree[child] += lazy[node]
                lazy[child] += lazy[node]
            lazy[node] = 0

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
    for r in range(n):
        # 열별 앞줄 최대 키 업데이트
        for c in range(m):
            if grid[r][c] > col_max[c]:
                col_max[c] = grid[r][c]

        # Segment Tree 초기화
        for i in range(k):
            tree[size + i] = i - (k - 1)
        for i in range(size - 1, 0, -1):
            tree[i] = max(tree[2 * i], tree[2 * i + 1])
        lazy = [0] * (2 * size)

        # 슬라이딩 윈도우
        for c in range(m):
            idx = bisect_right(h, col_max[c]) - 1
            if idx >= 0:
                update(1, 0, size - 1, 0, idx, 1)
            
            if c >= k - 1:
                if tree[1] <= 0:
                    ans += 1
                idx_out = bisect_right(h, col_max[c - k + 1]) - 1
                if idx_out >= 0:
                    update(1, 0, size - 1, 0, idx_out, -1)
                    
    print(ans)

if __name__ == "__main__":
    solve()