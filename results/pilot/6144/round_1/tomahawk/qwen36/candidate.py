import sys

def solve():
    input = sys.stdin.read
    data = input().split()
    
    n = int(data[0])
    q = int(data[1])
    
    ops = []
    boundaries = {1, n}
    
    idx = 2
    for _ in range(q):
        s = data[idx]
        x = int(data[idx+1])
        idx += 2
        ops.append((s, x))
        
        if s == 'D':
            boundaries.add(n - x + 1)
            boundaries.add(n - x)
        elif s == 'R':
            boundaries.add(n - x + 1)
            boundaries.add(n - x)
        elif s == 'L':
            boundaries.add(x)
            boundaries.add(x + 1)
            
    sorted_pts = sorted(list(boundaries))
    
    max_r = -float('inf')
    min_r = float('inf')
    max_c = -float('inf')
    min_c = float('inf')
    
    for pt in sorted_pts:
        if pt < 1 or pt > n:
            continue
            
        val_r = 0
        val_c = 0
        
        for s, x in ops:
            if s == 'D':
                if n - x + 1 <= pt <= n:
                    val_r += pt - n + x
            elif s == 'R':
                if n - x + 1 <= pt <= n:
                    val_c += pt - n + x
            elif s == 'L':
                if 1 <= pt <= x:
                    val_c += x - pt + 1
                    
        if val_r > max_r: max_r = val_r
        if val_r < min_r: min_r = val_r
        if val_c > max_c: max_c = val_c
        if val_c < min_c: min_c = val_c
        
    print((max_r + max_c) - (min_r + min_c))

if __name__ == '__main__':
    solve()