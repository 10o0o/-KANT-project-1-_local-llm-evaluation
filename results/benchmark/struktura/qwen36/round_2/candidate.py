import sys

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    n = int(input_data[0])
    k = int(input_data[1])
    
    if k < n:
        print(0)
        return
        
    MOD = 10**9 + 7
    
    def mat_mul(A, B):
        return [
            [(A[0][0] * B[0][0] + A[0][1] * B[1][0]) % MOD,
             (A[0][0] * B[0][1] + A[0][1] * B[1][1]) % MOD],
            [(A[1][0] * B[0][0] + A[1][1] * B[1][0]) % MOD,
             (A[1][0] * B[0][1] + A[1][1] * B[1][1]) % MOD]
        ]
    
    def mat_pow(A, p):
        res = [[1, 0], [0, 1]]
        while p > 0:
            if p & 1:
                res = mat_mul(res, A)
            A = mat_mul(A, A)
            p >>= 1
        return res
    
    # F_{n+1} is the top-left element of [[1,1],[1,0]]^n
    base_mat = [[1, 1], [1, 0]]
    fib_n_plus_1 = mat_pow(base_mat, n)[0][0]
    
    denom = pow(k, n, MOD)
    inv_denom = pow(denom, MOD - 2, MOD)
    
    ans = (fib_n_plus_1 * inv_denom) % MOD
    print(ans)

if __name__ == '__main__':
    solve()