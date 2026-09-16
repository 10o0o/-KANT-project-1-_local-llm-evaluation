import sys

MOD = 1_000_000_007

n, k = map(int, sys.stdin.buffer.read().split())

if k < n:
    print(0)
    sys.exit()

# Fast doubling으로 F_n, F_{n+1} 계산
f0, f1 = 0, 1

for bit in bin(n)[2:]:
    c = f0 * ((2 * f1 - f0) % MOD) % MOD
    d = (f0 * f0 + f1 * f1) % MOD

    if bit == '0':
        f0, f1 = c, d
    else:
        f0, f1 = d, (c + d) % MOD

structures = f1  # F_{n+1}

denominator = pow(k, n, MOD)
answer = structures * pow(denominator, MOD - 2, MOD) % MOD

print(answer)