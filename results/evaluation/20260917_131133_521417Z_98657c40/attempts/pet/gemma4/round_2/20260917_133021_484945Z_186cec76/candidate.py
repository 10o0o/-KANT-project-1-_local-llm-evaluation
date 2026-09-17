import sys

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    n = int(input_data[0])
    m = int(input_data[1])
    grid = input_data[2:]

    row_counts = [0] * n
    col_counts = [0] * m
    lilies = []

    for r in range(n):
        row_str = grid[r]
        for c in range(m):
            if row_str[c] == '1':
                row_counts[r] += 1
                col_counts[c] += 1
                lilies.append((r, c))

    row_sum_C_minus_1 = [0] * n
    col_sum_R_minus_1 = [0] * m
    
    for r, c in lilies:
        row_sum_C_minus_1[r] += (col_counts[c] - 1)
        col_sum_R_minus_1[c] += (row_counts[r] - 1)
        
    col_sum_f = [0] * m
    for r, c in lilies:
        f_rc = row_sum_C_minus_1[r] - (col_counts[c] - 1)
        col_sum_f[c] += f_rc
        
    total_paths = 0
    for r, c in lilies:
        f_rc = row_sum_C_minus_1[r] - (col_counts[c] - 1)
        g_rc = col_sum_f[c] - f_rc
        total_paths += (row_counts[r] - 1) * g_rc

    row_sum_h = [0] * n
    for r, c in lilies:
        h_rc = col_sum_R_minus_1[c] - (row_counts[r] - 1)
        row_sum_h[r] += h_rc
        
    col_sum_h = [0] * m
    for r, c in lilies:
        h_rc = col_sum_R_minus_1[c] - (row_counts[r] - 1)
        col_sum_h[c] += h_rc
        
    for r, c in lilies:
        h_rc = col_sum_R_minus_1[c] - (row_counts[r] - 1)
        row_sum_h_at_r = row_sum_h[r] - h_rc
        total_paths += (col_counts[c] - 1) * row_sum_h_at_r

    num_4_cycles = 0
    pair_counts = {}
    col_to_rows = [[] for _ in range(m)]
    for r, c in lilies:
        col_to_rows[c].append(r)
        
    for c in range(m):
        rows_in_col = col_to_rows[c]
        for i in range(len(rows_in_col)):
            for j in range(i + 1, len(rows_in_col)):
                r1, r2 = rows_in_col[i], rows_in_col[j]
                if r1 > r2: r1, r2 = r2, r1
                pair = (r1, r2)
                pair_counts[pair] = pair_counts.get(pair, 0) + 1
                
    for count in pair_counts.values():
        num_4_cycles += (count * (count - 1)) // 2
        
    print(total_paths - 2 * num_4_cycles)

if __name__ == "__main__":
    solve()