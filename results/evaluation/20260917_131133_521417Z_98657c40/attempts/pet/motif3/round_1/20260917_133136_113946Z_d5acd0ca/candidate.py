def main():
    import sys
    data = sys.stdin.read().splitlines()
    if not data:
        return
    n, m = map(int, data[0].split())
    grid = []
    for i in range(1, 1+n):
        grid.append(data[i].strip())
    
    def count_case(g):
        n_val = len(g)
        if n_val == 0:
            return 0
        m_val = len(g[0])
        R = [[] for _ in range(n_val)]
        C = [[] for _ in range(m_val)]
        for i in range(n_val):
            for j in range(m_val):
                if g[i][j] == '1':
                    R[i].append(j)
                    C[j].append(i)
        
        sizeR = [len(R[i]) for i in range(n_val)]
        sizeC = [len(C[j]) for j in range(m_val)]
        
        S_arr = [0] * n_val
        for i in range(n_val):
            total = 0
            for j in R[i]:
                total += (sizeC[j] - 1)
            S_arr[i] = total
        
        V_arr = [0] * m_val
        for j in range(m_val):
            total = 0
            for i in C[j]:
                total += S_arr[i]
            V_arr[j] = total
        
        F_diag = 0
        for i in range(n_val):
            if sizeR[i] > 0:
                F_diag += (sizeR[i] - 1) * (sizeR[i] - 1) * S_arr[i]
        
        part_sum = 0
        for i in range(n_val):
            if sizeR[i] == 0:
                continue
            s1 = 0
            s2 = 0
            for j in R[i]:
                s1 += V_arr[j]
                s2 += (sizeC[j] - 1) * sizeC[j]
            term = (sizeR[i] - 1) * (s1 - s2)
            part_sum += term
        
        F = part_sum - F_diag
        return F

    grid1 = [list(row) for row in grid]
    F1 = count_case(grid1)
    
    grid2 = [''.join(grid[i][j] for i in range(n)) for j in range(m)]
    F2 = count_case(grid2)
    
    print(F1 + F2)

if __name__ == "__main__":
    main()