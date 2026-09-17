import sys

read = sys.stdin.buffer.readline

n, q = map(int, read().split())
k = n // 2

sum_d = 0
down_n = 0

sum_l = 0
sum_r = 0

left_n = 0
right_n = 0

left_k = 0
left_k1 = 0
right_k = 0
right_k1 = 0

for _ in range(q):
    side, x = read().split()
    x = int(x)

    if side == b"D":
        sum_d += x
        if x == n:
            down_n += 1

    elif side == b"L":
        sum_l += x

        if x == n:
            left_n += 1
        if x == k:
            left_k += 1
        if x == k + 1:
            left_k1 += 1

    else:  # side == b"R"
        sum_r += x

        if x == n:
            right_n += 1
        if x == k:
            right_k += 1
        if x == k + 1:
            right_k1 += 1

row_range = sum_d - down_n

leftmost = sum_l + right_n
rightmost = sum_r + left_n
column_max = max(leftmost, rightmost)

if n == 1:
    column_min = leftmost
elif n % 2 == 0:
    column_min = min(left_k, right_k)
else:
    column_min = min(
        2 * left_k1 + left_k,
        left_k1 + right_k1,
        2 * right_k1 + right_k
    )

answer = row_range + column_max - column_min
print(answer)