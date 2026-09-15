import sys


def solve():
    MOD = 10**9 + 7

    line = sys.stdin.readline()
    if not line:
        return
    try:
        parts = line.split()
        if not parts:
            return
        n = int(parts[0])
        k = int(parts[1])

        if k < n:
            print(0)
            return
    except ValueError:
        return

    if n == 0:
        print(0)
        return

    def multiply(A, B):
        C00 = (A[0][0] * B[0][0] + A[0][1] * B[1][0]) % MOD
        C01 = (A[0][0] * B[0][1] + A[0][1] * B[1][1]) % MOD
        C10 = (A[1][0] * B[0][0] + A[1][1] * B[1][0]) % MOD
        C11 = (A[1][0] * B[0][1] + A[1][1] * B[1][1]) % MOD
        return [[C00, C01], [C10, C11]]

    def power(A, p):
        res = [[1, 0], [0, 1]]
        while p > 0:
            if p % 2 == 1:
                res = multiply(res, A)
            A = multiply(A, A)
            p //= 2
        return res

    T = [[1, 1], [1, 0]]
    T_n = power(T, n)
    S_n = T_n[0][0]

    total_arrays_inv = pow(pow(k, n, MOD), MOD - 2, MOD)

    ans = (S_n * total_arrays_inv) % MOD
    print(ans)


if __name__ == "__main__":
    solve()
