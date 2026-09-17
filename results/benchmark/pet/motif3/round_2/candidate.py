import sys

def main():
    data = sys.stdin.read().splitlines()
    if not data:
        return
    n, m = map(int, data[0].split())
    grid = []
    for i in range(1, 1+n):
        grid.append(data[i].strip())
    
    A = [[1 if ch == '1' else 0 for ch in row] for row in grid]
    
    row_list = []
    for i in range(n):
        row_list.append([j for j in range(m) if A[i][j] == 1])
    col_list = []
    for j in range(m):
        col_list.append([i for i in range(n) if A[i][j] == 1])
    
    dp0 = [[1 if A[i][j] else 0 for j in range(m)] for i in range(n)]
    
    row_sum0 = [sum(row) for row in dp0]
    col_sum0 = [sum(dp0[i][j] for i in range(n)) for j in range(m)]
    
    dp1 = [[[0, 0] for _ in range(m)] for __ in range(n)]
    for i in range(n):
        for j in range(m):
            if not A[i][j]:
                continue
            dp1[i][j][0] = row_sum0[i] - dp0[i][j]
            dp1[i][j][1] = col_sum0[j] - dp0[i][j]
    
    col0_sum1 = [0] * m
    row1_sum1 = [0] * n
    for i in range(n):
        for j in range(m):
            if not A[i][j]:
                continue
            col0_sum1[j] += dp1[i][j][0]
            row1_sum1[i] += dp1[i][j][1]
    
    dp2 = [[[0, 0] for _ in range(m)] for __ in range(n)]
    for i in range(n):
        for j in range(m):
            if not A[i][j]:
                continue
            dp2[i][j][0] = row1_sum1[i] - dp1[i][j][1]
            dp2[i][j][1] = col0_sum1[j] - dp1[i][j][0]
    
    col0_sum2 = [0] * m
    row1_sum2 = [0] * n
    for i in range(n):
        for j in range(m):
            if not A[i][j]:
                continue
            col0_sum2[j] += dp2[i][j][0]
            row1_sum2[i] += dp2[i][j][1]
    
    dp3 = [[[0, 0] for _ in range(m)] for __ in range(n)]
    for i in range(n):
        for j in range(m):
            if not A[i][j]:
                continue
            dp3[i][j][0] = row1_sum2[i] - dp2[i][j][1]
            dp3[i][j][1] = col0_sum2[j] - dp2[i][j][0]
    
    col0_sum3 = [0] * m
    row1_sum3 = [0] * n
    for i in range(n):
        for j in range(m):
            if not A[i][j]:
                continue
            col0_sum3[j] += dp3[i][j][0]
            row1_sum3[i] += dp3[i][j][1]
    
    dp4 = [[[0, 0] for _ in range(m)] for __ in range(n)]
    for i in range(n):
        for j in range(m):
            if not A[i][j]:
                continue
            dp4[i][j][0] = row1_sum3[i] - dp3[i][j][1]
            dp4[i][j][1] = col0_sum3[j] - dp3[i][j][0]
    
    total = 0
    for i in range(n):
        for j in range(m):
            if A[i][j]:
                total += dp4[i][j][0] + dp4[i][j][1]
    
    M = [[0] * m for _ in range(m)]
    for i in range(n):
        for idx1 in range(len(row_list[i])):
            j0 = row_list[i][idx1]
            for idx2 in range(idx1+1, len(row_list[i])):
                j1 = row_list[i][idx2]
                M[j0][j1] += 1
                M[j1][j0] += 1
    
    X = 0
    for j0 in range(m):
        for j1 in range(m):
            if j0 == j1:
                continue
            X += M[j0][j1] * (M[j0][j1] - 1)
    
    total_duplicates = 2 * X
    answer = total - total_duplicates
    print(answer)

if __name__ == '__main__':
    main()