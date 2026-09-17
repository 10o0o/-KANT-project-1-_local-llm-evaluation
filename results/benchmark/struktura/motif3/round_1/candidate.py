import sys

MOD = 1000000007

def fib(n: int) -> int:
    """Return the n-th Fibonacci number modulo MOD using fast doubling."""
    if n == 0:
        return 0
    a, b = 0, 1  # F_0, F_1
    for bit in bin(n)[2:]:  # iterate over bits from most significant to least
        # c = F_{2k}, d = F_{2k+1}
        c = (a * ((2 * b - a) % MOD)) % MOD
        d = (a * a + b * b) % MOD
        if bit == '1':
            a, b = d, (c + d) % MOD
        else:
            a, b = c, d
    return a

def main() -> None:
    data = sys.stdin.read().strip().split()
    if not data:
        return
    n = int(data[0])
    k = int(data[1])

    # If n > k, it's impossible to have all numbers 1..n in the array
    if n > k:
        print(0)
        return

    # Number of valid permutations of size n is F_{n+1}
    f = fib(n + 1)  # F_{n+1} mod MOD

    # Total number of possible arrays is k^n
    denom = pow(k, n, MOD)
    # Modular inverse of k^n
    inv_denom = pow(denom, MOD - 2, MOD)

    ans = f * inv_denom % MOD
    print(ans)

if __name__ == "__main__":
    main()