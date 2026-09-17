import sys

MOD = 1_000_000_007

n = int(sys.stdin.buffer.read())
print(pow(2, n // 2, MOD))