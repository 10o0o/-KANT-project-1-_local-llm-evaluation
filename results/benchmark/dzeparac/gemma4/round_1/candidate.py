import sys

def solve():
    # Read N from standard input
    input_data = sys.stdin.read().strip()
    if not input_data:
        return
    
    try:
        n = int(input_data)
    except ValueError:
        return

    # The number of ways is 2^(floor(n/2)) modulo 10^9 + 7
    # M = floor(n/2)
    m = n // 2
    MOD = 10**9 + 7
    
    # Calculate 2^m % MOD using modular exponentiation
    # pow(base, exp, mod) is efficient O(log exp)
    result = pow(2, m, MOD)
    
    # Print the result to standard output
    print(result)

if __name__ == "__main__":
    solve()