mod = 10**9 + 7

def matrix_mult(A, B, mod):
    n = len(A)
    m = len(B[0])
    p = len(B)
    C = [[0] * m for _ in range(n)]
    for i in range(n):
        for k in range(p):
            if A[i][k]:
                for j in range(m):
                    C[i][j] = (C[i][j] + A[i][k] * B[k][j]) % mod
    return C

def matrix_power(matrix, power, mod):
    n = len(matrix)
    result = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    base = matrix
    while power:
        if power & 1:
            result = matrix_mult(result, base, mod)
        base = matrix_mult(base, base, mod)
        power //= 2
    return result

def main():
    import sys
    data = sys.stdin.read().split()
    n = int(data[0])
    k = int(data[1])
    
    if k < n:
        print(0)
        return
        
    if n == 1:
        denom = pow(k, 1, mod)
        inv_denom = pow(denom, mod - 2, mod)
        ans = 1 * inv_denom % mod
        print(ans)
    elif n == 2:
        denom = pow(k, 2, mod)
        inv_denom = pow(denom, mod - 2, mod)
        ans = 2 * inv_denom % mod
        print(ans)
    else:
        T = [[0] * 9 for _ in range(9)]
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                i = (a + 1) * 3 + (b + 1)
                for c in (-1, 0, 1):
                    if (b, c) == (-1, 0) or (b, c) == (0, 1):
                        continue
                    if (a, c) == (-1, 1):
                        continue
                    j = (b + 1) * 3 + (c + 1)
                    T[i][j] = (T[i][j] + 1) % mod
        
        v0 = [0] * 9
        for c1 in (-1, 0):
            for c2 in (-1, 0, 1):
                if (c1, c2) == (-1, 0) or (c1, c2) == (0, 1):
                    continue
                idx = (c1 + 1) * 3 + (c2 + 1)
                v0[idx] = (v0[idx] + 1) % mod
        
        exp = n - 3
        if exp > 0:
            T_exp = matrix_power(T, exp, mod)
            v = [0] * 9
            for j in range(9):
                for i in range(9):
                    v[j] = (v[j] + v0[i] * T_exp[i][j]) % mod
        else:
            v = v0
        
        S = 0
        for idx in range(9):
            if v[idx] == 0:
                continue
            a1 = idx // 3
            b1 = idx % 3
            a = a1 - 1
            b = b1 - 1
            for c in [0, 1]:
                if (b, c) == (-1, 0) or (b, c) == (0, 1):
                    continue
                if (a, c) == (-1, 1):
                    continue
                S = (S + v[idx]) % mod
        
        denom = pow(k, n, mod)
        inv_denom = pow(denom, mod - 2, mod)
        ans = S * inv_denom % mod
        print(ans)

if __name__ == '__main__':
    main()