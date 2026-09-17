import sys

data = list(map(int, sys.stdin.buffer.read().split()))

n = data[0]
k = data[1]

strips = [n]
index = 2

for _ in range(k):
    x = data[index]
    l = data[index + 1]
    index += 2

    original_length = strips[x - 1]
    strips[x - 1:x] = [l, original_length - l]

print(len(set(strips)))