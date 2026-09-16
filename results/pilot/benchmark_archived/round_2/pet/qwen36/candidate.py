import sys

def solve():
    input = sys.stdin.read
    data = input().split()
    if not data:
        return
    
    n = int(data[0])
    m = int(data[1])
    grid = data[2:]
    
    # Precompute row and column counts
    R = [row.count('1') for row in grid]
    C = [0] * m
    for r in range(n):
        for c in range(m):
            if grid[r][c] == '1':
                C[c] += 1
                
    # Precompute T[r] = sum_{c: G[r][c]=1} (C[c]-1)
    T = [0] * n
    for r in range(n):
        s = 0
        for c in range(m):
            if grid[r][c] == '1':
                s += C[c] - 1
        T[r] = s
        
    # Compute A[c], B[c], D[c]
    A = [0] * m
    B = [0] * m
    D = [0] * m
    
    for r in range(n):
        if R[r] == 0:
            continue
        r_minus_1 = R[r] - 1
        for c in range(m):
            if grid[r][c] == '1':
                val = T[r] - (C[c] - 1)
                A[c] += r_minus_1
                B[c] += val
                D[c] += r_minus_1 * val
                
    total_hvhv = 0
    for c in range(m):
        total_hvhv += A[c] * B[c] - D[c]
        
    # Compute invalid paths (rectangles) using bitsets
    cols = [0] * m
    for r in range(n):
        mask = 0
        for c in range(m):
            if grid[r][c] == '1':
                mask |= (1 << r)
        cols[c] = mask
        
    invalid = 0
    for c1 in range(m):
        for c2 in range(c1 + 1, m):
            k = (cols[c1] & cols[c2]).bit_count()
            if k > 1:
                invalid += k * (k - 1)
                
    valid_hvhv = total_hvhv - invalid
    print(2 * valid_hvhv)

solve()