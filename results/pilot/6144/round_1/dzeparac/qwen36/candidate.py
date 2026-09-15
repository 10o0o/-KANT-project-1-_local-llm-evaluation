import sys

def solve():
    n = int(sys.stdin.read().strip())
    MOD = 10**9 + 7
    print(pow(2, n // 2, MOD))

if __name__ == '__main__':
    solve()