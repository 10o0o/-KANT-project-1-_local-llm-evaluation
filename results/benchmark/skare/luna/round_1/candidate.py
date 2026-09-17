import sys

data = list(map(int, sys.stdin.buffer.read().split()))
n, k = data[0], data[1]

pieces = [n]
pos = 2

for _ in range(k):
    x, l = data[pos], data[pos + 1]
    pos += 2

    old_length = pieces[x - 1]
    pieces[x - 1:x] = [l, old_length - l]

print(len(set(pieces)))