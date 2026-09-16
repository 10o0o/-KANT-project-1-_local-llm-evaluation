import sys

def solve():
    input = sys.stdin.read
    data = input().split()
    
    n = int(data[0])
    q = int(data[1])
    
    # Helper to compute max and min of a convex function defined by slope changes
    # The function value at index i is computed by accumulating slope changes.
    # We track events: (position, slope_change)
    # We evaluate at boundaries (1 and n) and at each event position.
    
    def compute_extremes(n, events):
        # events: list of (pos, delta_slope)
        # We need to compute f(i) for i in [1, n]
        # f(i) = f(i-1) + current_slope
        # Initially f(1) = 0, slope = 0
        
        # Sort events by position
        events.sort(key=lambda x: x[0])
        
        max_val = 0
        min_val = 0
        
        current_val = 0
        current_slope = 0
        idx = 0
        num_events = len(events)
        
        # Evaluate at i = 1
        max_val = max(max_val, current_val)
        min_val = min(min_val, current_val)
        
        # Process intervals
        prev_pos = 1
        while idx < num_events:
            pos, delta = events[idx]
            
            # Move from prev_pos to pos
            # The slope is constant in [prev_pos, pos-1]
            # We need to check values at prev_pos (already done) and pos
            # Actually, since it's convex, min could be at pos. Max is at boundaries.
            # We just step through events.
            
            # Update slope for the range [prev_pos, pos-1]
            # Value at pos = value at prev_pos + slope * (pos - prev_pos)
            current_val += current_slope * (pos - prev_pos)
            current_slope += delta
            prev_pos = pos
            
            max_val = max(max_val, current_val)
            min_val = min(min_val, current_val)
            
            idx += 1
            
        # After last event, move to n
        if prev_pos < n:
            current_val += current_slope * (n - prev_pos)
            max_val = max(max_val, current_val)
            min_val = min(min_val, current_val)
            
        return max_val, min_val

    # Process Row contributions (D operations)
    # D x: adds (r - (n-x)) for r in [n-x+1, n]
    # This increases slope by +1 in [n-x+1, n]
    row_events = []
    for _ in range(q):
        s = data[2 + 3 * _]
        x = int(data[3 + 3 * _])
        if s == 'D':
            L = n - x + 1
            R = n
            row_events.append((L, 1))
            if R + 1 <= n:
                row_events.append((R + 1, -1))
                
    r_max, r_min = compute_extremes(n, row_events)
    
    # Process Column contributions (L and R operations)
    # L x: adds (x - c + 1) for c in [1, x] -> slope decreases by 1 in [1, x]
    # R x: adds (x - (n-c)) for c in [n-x+1, n] -> slope increases by 1 in [n-x+1, n]
    col_events = []
    for _ in range(q):
        s = data[2 + 3 * _]
        x = int(data[3 + 3 * _])
        if s == 'L':
            L = 1
            R = x
            col_events.append((L, -1))
            if R + 1 <= n:
                col_events.append((R + 1, 1))
        elif s == 'R':
            L = n - x + 1
            R = n
            col_events.append((L, 1))
            if R + 1 <= n:
                col_events.append((R + 1, -1))
                
    c_max, c_min = compute_extremes(n, col_events)
    
    print((r_max - r_min) + (c_max - c_min))

solve()