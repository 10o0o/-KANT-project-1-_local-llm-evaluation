import sys

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    n = int(input_data[0])
    k = int(input_data[1])
    MOD = 10**9 + 7

    # k < n이면 1~n을 모두 포함할 수 없으므로 확률은 0
    if k < n:
        print(0)
        return

    # Fast Doubling 기법을 이용한 피보나치 수 계산 O(log n)
    def fib(n):
        a, b = 0, 1
        for bit in bin(n)[2:]:
            c = a * (2 * b - a) % MOD
            d = (a * a + b * b) % MOD
            if bit == '0':
                a, b = c, d
            else:
                a, b = d, (c + d) % MOD
        return a

    # 유리한 경우의 수: F_{n+1}
    favorable = fib(n + 1)
    # 전체 경우의 수: k^n
    total = pow(k, n, MOD)
    # 모듈러 역원: total^(MOD-2) % MOD
    inv_total = pow(total, MOD - 2, MOD)

    print((favorable * inv_total) % MOD)

if __name__ == '__main__':
    solve()