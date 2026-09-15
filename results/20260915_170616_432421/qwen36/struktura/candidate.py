import sys

def solve():
    MOD = 10**9 + 7
    
    def mat_mul(A, B):
        C = [[0, 0], [0, 0]]
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    C[i][j] = (C[i][j] + A[i][k] * B[k][j]) % MOD
        return C

    def mat_pow(A, p):
        res = [[1, 0], [0, 1]]
        while p > 0:
            if p & 1:
                res = mat_mul(res, A)
            A = mat_mul(A, A)
            p >>= 1
        return res

    def fib(n):
        if n == 0: return 0
        if n == 1: return 1
        M = [[1, 1], [1, 0]]
        res = mat_pow(M, n - 1)
        return res[0][0]

    def power(a, b):
        res = 1
        a %= MOD
        while b > 0:
            if b & 1:
                res = res * a % MOD
            a = a * a % MOD
            b >>= 1
        return res

    def modinv(a):
        return power(a, MOD - 2)

    input_data = sys.stdin.read().split()
    if not input_data:
        return
    n = int(input_data[0])
    k = int(input_data[1])

    if k < n:
        print(0)
        return

    fn = fib(n)
    kn_inv = modinv(power(k, n))
    
    ans = fn * kn_inv % MOD
    print(ans)

if __name__ == '__main__':
    solve()