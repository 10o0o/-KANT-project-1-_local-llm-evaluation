import sys

MOD = 10**9 + 7
n = int(sys.stdin.buffer.readline())

print(pow(2, n // 2, MOD))