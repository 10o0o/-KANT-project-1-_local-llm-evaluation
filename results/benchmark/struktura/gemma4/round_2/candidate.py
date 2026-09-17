import sys

def mat_mul(A, B, mod):
    C = [[0, 0], [0, 0]]
    for i in range(2):
        for j in range(2):
            for l in range(2):
                C[i][j] = (C[i][j] + A[i][l] * B[l][j]) % mod
    return C

def mat_pow(A, p, mod):
    res = [[1, 0], [0, 1]]
    while p > 0:
        if p % 2 == 1:
            res = mat_mul(res, A, mod)
        A = mat_mul(A, A, mod)
        p //= 2
    return res

def main():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    n = int(input_data[0])
    k = int(input_data[1])
    
    MOD = 10**9 + 7
    
    if k < n:
        print(0)
        return

    T = [[1, 1], [1, 0]]
    T_n = mat_pow(T, n, MOD)
    f_n_plus_1 = T_n[0][0]
    
    k_n = pow(k, n, MOD)
    k_n_inv = pow(k_n, MOD - 2, MOD)
    
    ans = (f_n_plus_1 * k_n_inv) % MOD
    print(ans)

if __name__ == "__main__":
    main()