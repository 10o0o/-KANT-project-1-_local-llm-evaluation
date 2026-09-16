import sys

def solve():
    input = sys.stdin.read
    data = input().split()
    
    n = int(data[0])
    q = int(data[1])
    
    row_events = {}
    col_events = {}
    
    idx = 2
    for _ in range(q):
        side = data[idx]
        x = int(data[idx+1])
        idx += 2
        
        if side == 'D':
            # Range [n-x+1, n], adds (i - (n-x))
            # slope += 1, const += -(n-x)
            L = n - x + 1
            R = n
            delta_s = 1
            delta_c = -(n - x)
            
            row_events[L] = row_events.get(L, [0, 0])
            row_events[L][0] += delta_s
            row_events[L][1] += delta_c
            
            if R + 1 <= n:
                row_events[R + 1] = row_events.get(R + 1, [0, 0])
                row_events[R + 1][0] -= delta_s
                row_events[R + 1][1] -= delta_c
                
        elif side == 'L':
            # Range [1, x], adds (x+1 - c)
            # slope += -1, const += (x+1)
            L = 1
            R = x
            delta_s = -1
            delta_c = x + 1
            
            col_events[L] = col_events.get(L, [0, 0])
            col_events[L][0] += delta_s
            col_events[L][1] += delta_c
            
            if R + 1 <= n:
                col_events[R + 1] = col_events.get(R + 1, [0, 0])
                col_events[R + 1][0] -= delta_s
                col_events[R + 1][1] -= delta_c
                
        elif side == 'R':
            # Range [n-x+1, n], adds (c - (n-x))
            # slope += 1, const += -(n-x)
            L = n - x + 1
            R = n
            delta_s = 1
            delta_c = -(n - x)
            
            col_events[L] = col_events.get(L, [0, 0])
            col_events[L][0] += delta_s
            col_events[L][1] += delta_c
            
            if R + 1 <= n:
                col_events[R + 1] = col_events.get(R + 1, [0, 0])
                col_events[R + 1][0] -= delta_s
                col_events[R + 1][1] -= delta_c

    def get_min_max_diff(events, n):
        if not events:
            return 0
        
        points = sorted(set(list(events.keys()) + [1, n]))
        
        cur_s = 0
        cur_c = 0
        min_val = 0
        max_val = 0
        
        for p in points:
            if p in events:
                cur_s += events[p][0]
                cur_c += events[p][1]
            
            val = cur_s * p + cur_c
            if val < min_val:
                min_val = val
            if val > max_val:
                max_val = val
                
        return max_val - min_val

    row_diff = get_min_max_diff(row_events, n)
    col_diff = get_min_max_diff(col_events, n)
    
    print(row_diff + col_diff)

solve()