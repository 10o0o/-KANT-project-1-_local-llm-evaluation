import sys

MOD = 1_000_000_007

n, k = map(int, sys.stdin.buffer.read().split())

if k < n:
    print(0)
else:
    def fib_pair(x):
        if x == 0:
            return 0, 1

        a, b = fib_pair(x // 2)

        c = a * ((2 * b - a) % MOD) % MOD
        d = (a * a + b * b) % MOD

        if x & 1:
            return d, (c + d) % MOD
        return c, d

    count, _ = fib_pair(n + 1)
    denominator = pow(k, n, MOD)
    answer = count * pow(denominator, MOD - 2, MOD) % MOD

    print(answer)