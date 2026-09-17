import bisect

def main():
    import sys
    data = sys.stdin.read().splitlines()
    if not data:
        print(0)
        return
    n, q = map(int, data[0].split())
    D_ops = []
    R_ops = []
    L_ops = []
    index = 1
    for i in range(q):
        parts = data[index].split()
        index += 1
        if not parts:
            continue
        s = parts[0]
        x = int(parts[1])
        if s == 'D':
            D_ops.append(x)
        elif s == 'R':
            R_ops.append(x)
        elif s == 'L':
            L_ops.append(x)
    
    critical_i = set()
    critical_i.add(0)
    critical_i.add(n-1)
    for x in D_ops:
        t = n - x
        if 0 <= t <= n-1:
            critical_i.add(t)
    
    critical_j = set()
    critical_j.add(0)
    critical_j.add(n-1)
    for x in R_ops:
        t = n - x
        if 0 <= t <= n-1:
            critical_j.add(t)
        if 0 <= t-1 <= n-1:
            critical_j.add(t-1)
    for x in L_ops:
        if 0 <= x-1 <= n-1:
            critical_j.add(x-1)
        if 0 <= x <= n-1:
            critical_j.add(x)
    
    D_ops_sorted = sorted(D_ops)
    m_d = len(D_ops_sorted)
    suffix_sum_D = [0] * (m_d + 1)
    for i in range(m_d-1, -1, -1):
        suffix_sum_D[i] = suffix_sum_D[i+1] + D_ops_sorted[i]
    
    R_ops_sorted = sorted(R_ops)
    m_r = len(R_ops_sorted)
    suffix_sum_R = [0] * (m_r + 1)
    for i in range(m_r-1, -1, -1):
        suffix_sum_R[i] = suffix_sum_R[i+1] + R_ops_sorted[i]
    
    L_ops_sorted = sorted(L_ops)
    m_l = len(L_ops_sorted)
    suffix_sum_L = [0] * (m_l + 1)
    for i in range(m_l-1, -1, -1):
        suffix_sum_L[i] = suffix_sum_L[i+1] + L_ops_sorted[i]
    
    critical_i_sorted = sorted(critical_i)
    A_vals = []
    for i in critical_i_sorted:
        t = n - i
        idx = bisect.bisect_left(D_ops_sorted, t)
        count = m_d - idx
        total_x = suffix_sum_D[idx]
        A_val = count * i + total_x - (n-1) * count
        A_vals.append(A_val)
    
    critical_j_sorted = sorted(critical_j)
    D_vals = []
    for j in critical_j_sorted:
        t_r = n - j
        idx_r = bisect.bisect_left(R_ops_sorted, t_r)
        count_r = m_r - idx_r
        total_x_r = suffix_sum_R[idx_r]
        B_val = count_r * j + total_x_r - (n-1) * count_r
        
        idx_l = bisect.bisect_right(L_ops_sorted, j)
        count_l = m_l - idx_l
        total_x_l = suffix_sum_L[idx_l]
        C_val = total_x_l - j * count_l
        
        D_val = B_val + C_val
        D_vals.append(D_val)
    
    minA = min(A_vals) if A_vals else 0
    maxA = max(A_vals) if A_vals else 0
    minD = min(D_vals) if D_vals else 0
    maxD = max(D_vals) if D_vals else 0
    
    ans = (maxA + maxD) - (minA + minD)
    print(ans)

if __name__ == "__main__":
    main()