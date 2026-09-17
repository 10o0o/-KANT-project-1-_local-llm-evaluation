import sys

def solve():
    # Read N from standard input
    line = sys.stdin.readline()
    if not line:
        return
    n = int(line.strip())
    
    # The formula derived is 2^(floor(N/2)) modulo 10^9 + 7
    # We use modular exponentiation for efficiency
    MOD = 10**9 + 7
    
    # Calculate floor(N/2)
    exponent = n // 2
    
    # Calculate 2^exponent % MOD
    result = pow(2, exponent, MOD)
    
    # Print the result to standard output
    print(result)

if __name__ == "__main__":
    solve()