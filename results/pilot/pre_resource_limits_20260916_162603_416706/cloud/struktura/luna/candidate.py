import sys

MOD = 1_000_000_007


def fibonacci_pair(x):
    """(F_x, F_{x+1})를 반환한다."""
    if x == 0:
        return 0, 1

    a, b = fibonacci_pair(x // 2)

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

    structure_count = fibonacci_pair(n + 1)[0]
    total_count = pow(k, n, MOD)
    inverse_total_count = pow(total_count, MOD - 2, MOD)

    answer = structure_count * inverse_total_count % MOD
    print(answer)


if __name__ == "__main__":
    main()