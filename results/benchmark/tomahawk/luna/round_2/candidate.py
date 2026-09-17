import sys
from bisect import bisect_left


def make_suffix(values):
    suffix = [0] * (len(values) + 1)
    for i in range(len(values) - 1, -1, -1):
        suffix[i] = suffix[i + 1] + values[i]
    return suffix


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return

    n = int(data[0])
    q = int(data[1])

    left_values = []
    right_values = []

    row_max = 0
    row_min = 0

    index = 2
    for _ in range(q):
        side = data[index]
        x = int(data[index + 1])
        index += 2

        if side == b"L":
            left_values.append(x)
        elif side == b"R":
            right_values.append(x)
        else:  # D
            row_max += x
            row_min += max(0, x - n + 1)

    left_values.sort()
    right_values.sort()

    left_suffix = make_suffix(left_values)
    right_suffix = make_suffix(right_values)

    left_count_total = len(left_values)
    right_count_total = len(right_values)

    def column_value(c):
        # L 연산들의 기여
        i = bisect_left(left_values, c)
        left_count = left_count_total - i
        left_part = left_suffix[i] - (c - 1) * left_count

        # R 연산들의 기여
        threshold = n - c + 1
        j = bisect_left(right_values, threshold)
        right_count = right_count_total - j
        right_part = right_suffix[j] - (n - c) * right_count

        return left_part + right_part

    column_at_first = column_value(1)
    column_at_last = column_value(n)
    column_max = max(column_at_first, column_at_last)

    if n == 1:
        column_min = column_at_first
    else:
        def delta(c):
            # B(c+1) - B(c)
            i = bisect_left(left_values, c)
            left_active = left_count_total - i

            j = bisect_left(right_values, n - c)
            right_active = right_count_total - j

            return -left_active + right_active

        low, high = 1, n - 1
        first_nonnegative = n

        while low <= high:
            mid = (low + high) // 2
            if delta(mid) >= 0:
                first_nonnegative = mid
                high = mid - 1
            else:
                low = mid + 1

        if first_nonnegative == n:
            column_min = column_at_last
        else:
            column_min = column_value(first_nonnegative)

    answer = (row_max - row_min) + (column_max - column_min)
    print(answer)


if __name__ == "__main__":
    main()