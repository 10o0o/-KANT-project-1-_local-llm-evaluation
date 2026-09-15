import sys

def solve():
    MOD = 10**9 + 7
    
    input = sys.stdin.read
    data = input().split()
    if not data:
        return
    n = int(data[0])
    k = int(data[1])
    
    if k < n:
        print(0)
        return
    
    def mat_mul(A, B):
        C = [[0, 0], [0, 0]]
        for i in range(2):
            for j in range(2):
                for l in range(2):
                    C[i][j] = (C[i][j] + A[i][l] * B[l][j]) % MOD
        return C
    
    def mat_pow(A, p):
        res = [[1, 0], [0, 1]]
        while p > 0:
            if p % 2 == 1:
                res = mat_mul(res, A)
            A = mat_mul(A, A)
            p //= 2
        return res
    
    if n == 1:
        fn = 1
    elif n == 2:
        fn = 2
    else:
        base = [[1, 1], [1, 0]]
        res_mat = mat_pow(base, n - 2)
        fn = (res_mat[0][0] * 2 + res_mat[0][1] * 1) % MOD
    
    denom = pow(k, n, MOD)
    inv_denom = pow(denom, MOD - 2, MOD)
    
    ans = (fn * inv_denom) % MOD
    print(ans)

solve()