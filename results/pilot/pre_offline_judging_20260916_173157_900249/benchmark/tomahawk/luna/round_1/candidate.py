import sys
from bisect import bisect_left, bisect_right

tokens = sys.stdin.buffer.read().split()
if not tokens:
    sys.exit(0)

n = int(tokens[0])
q = int(tokens[1])

left_lengths = []
right_starts = []

down_bottom = 0
down_top = 0

idx = 2
for _ in range(q):
    side = tokens[idx]
    x = int(tokens[idx + 1])
    idx += 2

    if side == b'D':
        down_bottom += x
        if x == n:
            down_top += 1
    elif side == b'L':
        left_lengths.append(x)
    else:  # side == b'R'
        right_starts.append(n - x)

left_lengths.sort()
right_starts.sort()

left_count = len(left_lengths)


def slope(j):
    right_active = bisect_right(right_starts, j)
    left_active = left_count - bisect_left(left_lengths, j)
    return right_active - left_active


if n == 1:
    minimum_position = 1
else:
    lo = 1
    hi = n - 1
    minimum_position = n

    while lo <= hi:
        mid = (lo + hi) // 2
        if slope(mid) >= 0:
            minimum_position = mid
            hi = mid - 1
        else:
            lo = mid + 1


def column_value(j):
    total = 0

    for x in left_lengths:
        if x >= j:
            total += x + 1 - j

    for start in right_starts:
        if start < j:
            total += j - start

    return total


first_column = column_value(1)
last_column = column_value(n)
minimum_column = column_value(minimum_position)

column_range = max(first_column, last_column) - minimum_column
row_range = down_bottom - down_top

answer = row_range + column_range
print(answer)