import sys
from bisect import bisect_left

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    n = int(input_data[0])
    q = int(input_data[1])
    
    d_ops_x = []
    d_ops_n = 0
    l_vals = []
    r_vals = []
    
    idx = 2
    for _ in range(q):
        s = input_data[idx]
        x = int(input_data[idx+1])
        idx += 2
        if s == 'D':
            d_ops_x.append(x)
            if x == n:
                d_ops_n += 1
        elif s == 'L':
            l_vals.append(x)
        elif s == 'R':
            r_vals.append(x)
            
    # R_i part
    max_r = sum(d_ops_x)
    min_r = d_ops_n
    r_diff = max_r - min_r
    
    # C_j part
    l_vals.sort()
    r_vals.sort()
    
    l_suffix_x_plus_1 = [0] * (len(l_vals) + 1)
    l_suffix_count = [0] * (len(l_vals) + 1)
    for i in range(len(l_vals) - 1, -1, -1):
        l_suffix_x_plus_1[i] = l_suffix_x_plus_1[i+1] + (l_vals[i] + 1)
        l_suffix_count[i] = l_suffix_count[i+1] + 1
        
    r_suffix_x_minus_n = [0] * (len(r_vals) + 1)
    r_suffix_count = [0] * (len(r_vals) + 1)
    for i in range(len(r_vals) - 1, -1, -1):
        r_suffix_x_minus_n[i] = r_suffix_x_minus_n[i+1] + (r_vals[i] - n)
        r_suffix_count[i] = r_suffix_count[i+1] + 1
        
    breakpoints = {1, n}
    for x in l_vals:
        if 1 <= x <= n: breakpoints.add(x)
        if 1 <= x + 1 <= n: breakpoints.add(x + 1)
    for x in r_vals:
        if 1 <= n - x <= n: breakpoints.add(n - x)
        if 1 <= n - x + 1 <= n: breakpoints.add(n - x + 1)
        
    max_c = -float('inf')
    min_c = float('inf')
    
    # If no L or R operations, C_j is always 0
    if not l_vals and not r_vals:
        max_c = 0
        min_c = 0
    else:
        for j in sorted(list(breakpoints)):
            # C_j = C_j_L + C_j_R
            # C_j_L = sum_{x in L, x >= j} (x - j + 1)
            # C_j_R = sum_{x in R, x >= n - j + 1} (x - n + j)
            
            c_j_l = 0
            idx_l = bisect_left(l_vals, j)
            if idx_l < len(l_vals):
                c_j_l = l_suffix_x_plus_1[idx_l] - j * l_suffix_count[idx_l]
                
            c_j_r = 0
            idx_r = bisect_left(r_vals, n - j + 1)
            if idx_r < len(r_vals):
                c_j_r = r_suffix_x_minus_n[idx_r] + j * r_suffix_count[idx_r]
                
            c_j = c_j_l + c_j_r
            if c_j > max_c: max_c = c_j
            if c_j < min_c: min_c = c_j
            
        # Also consider the case where C_j is 0 (for j not covered by any L or R)
        if not l_vals and not r_vals:
            max_c = 0
            min_c = 0
        elif not l_vals or not r_vals:
            # If one set is empty, C_j could be 0
            # Check if 0 is a possible value for C_j
            # For L, C_j is 0 if j > max(l_vals). For R, C_j is 0 if j < min(n-x+1)
            # We already check breakpoints, but we should ensure 0 is considered.
            # However, the breakpoints already cover the boundaries.
            # Let's check if 0 is a possible value.
            pass

        # To be safe, if there's any j such that C_j = 0, we should include it.
        # The minimum possible value of C_j is 0 because all increases are positive.
        # The maximum possible value is at least 0.
        # Let's check if 0 is a possible value for C_j.
        # C_j is 0 if j is not in any L range [1, x] and not in any R range [n-x+1, n].
        # This is possible if there's some j in [1, n] not covered.
        # We can check this by looking at the gaps in the union of all [1, x] and [n-x+1, n].
        # But since we only need max_c and min_c, and C_j >= 0, min_c is 0 if any j is not covered.
        # Let's check if any j in [1, n] is not covered.
        
        # A simpler way: the minimum value of C_j is 0 if there's any j not covered.
        # The maximum value of C_j is at least 0.
        # Let's check if 0 is a possible value for C_j.
        # We can check if the union of all [1, x] and [n-x+1, n] covers [1, n].
        # The union of [1, x] is [1, max(l_vals)].
        # The union of [n-x+1, n] is [min(n-x+1), n].
        # So the union is [1, max(l_vals)] U [min(n-x+1), n].
        # This covers [1, n] if max(l_vals) >= min(n-x+1) - 1.
        
        max_l = max(l_vals) if l_vals else 0
        min_r_start = min([n - x + 1 for x in r_vals]) if r_vals else n + 1
        
        if max_l < min_r_start - 1:
            # There is a gap where C_j = 0
            min_c = min(min_c, 0)
        
        # Also, if there are no L or R operations, C_j is 0.
        if not l_vals and not r_vals:
            max_c = 0
            min_c = 0
        elif not l_vals:
            # C_j is 0 for j < min_r_start
            if min_r_start > 1:
                min_c = min(min_c, 0)
        elif not r_vals:
            # C_j is 0 for j > max_l
            if max_l < n:
                min_c = min(min_c, 0)

    print(r_diff + (max_c - min_c))

if __name__ == "__main__":
    solve()