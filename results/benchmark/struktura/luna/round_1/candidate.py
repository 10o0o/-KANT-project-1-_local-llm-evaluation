import sys

MOD = 1_000_000_007


def fib_pair(x):
    # (F_x, F_{x+1})를 반환
    if x == 0:
        return 0, 1

    a, b = fib_pair(x // 2)

    c = a * ((2 * b - a) % MOD) % MOD
    d = (a * a + b * b) % MOD

    if x % 2 == 0:
        return c, d
    return d, (c + d) % MOD


def main():
    n, k = map(int, sys.stdin.buffer.readline().split())

    if k < n:
        print(0)
        return

    favorable, _ = fib_pair(n + 1)
    total = pow(k, n, MOD)
    answer = favorable * pow(total, MOD - 2, MOD) % MOD

    print(answer)


if __name__ == "__main__":
    main()