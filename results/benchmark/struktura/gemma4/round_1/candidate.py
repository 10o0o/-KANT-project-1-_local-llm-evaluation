import sys

def solve():
    # Read n and k from standard input
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    n = int(input_data[0])
    k = int(input_data[1])
    
    MOD = 10**9 + 7
    
    # If k < n, it's impossible to have a permutation of 1 to n
    if k < n:
        print(0)
        return

    # Function for matrix multiplication modulo MOD
    def multiply(A, B, mod):
        C = [[0, 0], [0, 0]]
        for i in range(2):
            for j in range(2):
                for l in range(2):
                    C[i][j] = (C[i][j] + A[i][l] * B[l][j]) % mod
        return C

    # Function for matrix exponentiation modulo MOD
    def power(A, p, mod):
        res = [[1, 0], [0, 1]]
        while p > 0:
            if p % 2 == 1:
                res = multiply(res, A, mod)
            A = multiply(A, A, mod)
            p //= 2
        return res

    # The number of structures is the (n+1)-th Fibonacci number
    # F_1 = 1, F_2 = 1, F_3 = 2, ...
    # We use matrix exponentiation to find F_{n+1}
    # [F_{m+1}, F_m] = [[1, 1], [1, 0]] * [F_m, F_{m-1}]
    # So [F_{n+1}, F_n] = [[1, 1], [1, 0]]^n * [F_1, F_0] where F_1=1, F_0=0
    if n == 0:
        # This case is not possible based on constraints (n >= 1)
        print(0)
        return
    
    T = [[1, 1], [1, 0]]
    T_n = power(T, n, MOD)
    # F_{n+1} is the top-left element of T^n if we consider F_1=1, F_0=0
    # Actually, T^n * [F_1, F_0]^T = [F_{n+1}, F_n]^T
    # Since F_1=1 and F_0=0, F_{n+1} is T_n[0][0]
    f_n_plus_1 = T_n[0][0]
    
    # Calculate k^n modulo MOD
    k_n = pow(k, n, MOD)
    
    # Calculate the modular inverse of k^n
    k_n_inv = pow(k_n, MOD - 2, MOD)
    
    # The answer is (F_{n+1} * k_n_inv) % MOD
    ans = (f_n_plus_1 * k_n_inv) % MOD
    print(ans)

if __name__ == "__main__":
    solve