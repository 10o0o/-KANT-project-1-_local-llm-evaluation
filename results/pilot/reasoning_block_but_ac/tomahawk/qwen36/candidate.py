import sys

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    n = int(input_data[0])
    q = int(input_data[1])
    
    row_events = {}
    col_events = {}
    
    idx = 2
    for _ in range(q):
        s = input_data[idx]
        x = int(input_data[idx+1])
        idx += 2
        
        if s == 'D':
            # Down: affects rows [n-x+1, n]
            # Adds (i - (n-x)) to row i
            # Slope +1, Const -(n-x)
            L = n - x + 1
            R = n
            ds = 1
            dc = -(n - x)
            
            if L not in row_events: row_events[L] = [0, 0]
            row_events[L][0] += ds
            row_events[L][1] += dc
            if R + 1 not in row_events: row_events[R + 1] = [0, 0]
            row_events[R + 1][0] -= ds
            row_events[R + 1][1] -= dc
            
        elif s == 'L':
            # Left: affects cols [1, x]
            # Adds (x+1 - c) to col c
            # Slope -1, Const x+1
            L = 1
            R = x
            ds = -1
            dc = x + 1
            
            if L not in col_events: col_events[L] = [0, 0]
            col_events[L][0] += ds
            col_events[L][1] += dc
            if R + 1 not in col_events: col_events[R + 1] = [0, 0]
            col_events[R + 1][0] -= ds
            col_events[R + 1][1] -= dc
            
        elif s == 'R':
            # Right: affects cols [n-x+1, n]
            # Adds (c - (n-x)) to col c
            # Slope +1, Const -(n-x)
            L = n - x + 1
            R = n
            ds = 1
            dc = -(n - x)
            
            if L not in col_events: col_events[L] = [0, 0]
            col_events[L][0] += ds
            col_events[L][1] += dc
            if R + 1 not in col_events: col_events[R + 1] = [0, 0]
            col_events[R + 1][0] -= ds
            col_events[R + 1][1] -= dc

    def compute_diff(events, limit):
        # Collect all critical points within [1, limit]
        points = set()
        points.add(1)
        points.add(limit)
        for p in events:
            if 1 <= p <= limit:
                points.add(p)
            if 1 <= p - 1 <= limit:
                points.add(p - 1)
                
        sorted_points = sorted(points)
        
        cur_s = 0
        cur_c = 0
        min_val = float('inf')
        max_val = float('-inf')
        
        for p in sorted_points:
            if p in events:
                cur_s += events[p][0]
                cur_c += events[p][1]
            
            val = cur_s * p + cur_c
            if val < min_val: min_val = val
            if val > max_val: max_val = val
            
        return max_val - min_val

    row_diff = compute_diff(row_events, n)
    col_diff = compute_diff(col_events, n)
    
    print(row_diff + col_diff)

if __name__ == '__main__':
    solve()