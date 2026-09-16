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
        x = int(input_data[idx + 1])
        idx += 2
        
        if s == 'D':
            L = n - x + 1
            R = n
            delta_s = 1
            delta_c = -(n - x)
            if L not in row_events: row_events[L] = [0, 0]
            row_events[L][0] += delta_s
            row_events[L][1] += delta_c
            if R + 1 not in row_events: row_events[R + 1] = [0, 0]
            row_events[R + 1][0] -= delta_s
            row_events[R + 1][1] -= delta_c
            
        elif s == 'L':
            L = 1
            R = x
            delta_s = -1
            delta_c = x + 1
            if L not in col_events: col_events[L] = [0, 0]
            col_events[L][0] += delta_s
            col_events[L][1] += delta_c
            if R + 1 not in col_events: col_events[R + 1] = [0, 0]
            col_events[R + 1][0] -= delta_s
            col_events[R + 1][1] -= delta_c
            
        elif s == 'R':
            L = n - x + 1
            R = n
            delta_s = 1
            delta_c = -(n - x)
            if L not in col_events: col_events[L] = [0, 0]
            col_events[L][0] += delta_s
            col_events[L][1] += delta_c
            if R + 1 not in col_events: col_events[R + 1] = [0, 0]
            col_events[R + 1][0] -= delta_s
            col_events[R + 1][1] -= delta_c

    def compute_diff(events, n):
        if not events:
            return 0
        
        positions = set(events.keys())
        positions.add(1)
        positions.add(n)
        sorted_pos = sorted([p for p in positions if 1 <= p <= n])
        
        cur_s = 0
        cur_c = 0
        min_v = None
        max_v = None
        
        for p in sorted_pos:
            if p in events:
                cur_s += events[p][0]
                cur_c += events[p][1]
            v = cur_s * p + cur_c
            if min_v is None or v < min_v:
                min_v = v
            if max_v is None or v > max_v:
                max_v = v
                
        return max_v - min_v

    print(compute_diff(row_events, n) + compute_diff(col_events, n))

if __name__ == '__main__':
    solve()