import sys

MOD = 10**9 + 7

def fib(n):
    if n == 0:
        return (0, 1)
    a, b = fib(n >> 1)
    c = (a * ((b << 1) - a)) % MOD
    d = (a * a + b * b) % MOD
    if n & 1:
        return (d, (c + d) % MOD)
    return (c, d)

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    n = int(input_data[0])
    k = int(input_data[1])
    
    if k < n:
        print(0)
        return
        
    # F_{n+1} 계산
    _, fn_plus_1 = fib(n + 1)
    
    # k^n 계산
    k_pow_n = pow(k, n, MOD)
    
    # k^n의 모듈러 역수 계산
    inv_k_pow_n = pow(k_pow_n, MOD - 2, MOD)
    
    # 결과 출력
    ans = (fn_plus_1 * inv_k_pow_n) % MOD
    print(ans)

if __name__ == '__main__':
    solve()