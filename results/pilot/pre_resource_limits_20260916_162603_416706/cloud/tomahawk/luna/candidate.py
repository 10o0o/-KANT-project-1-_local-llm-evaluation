import sys


def main():
    data = sys.stdin.buffer.read().split()

    n = int(data[0])
    q = int(data[1])

    left_lengths = []
    right_starts = []
    vertical_range = 0

    index = 2

    for _ in range(q):
        side = data[index]
        x = int(data[index + 1])
        index += 2

        if side == b"L":
            left_lengths.append(x)
        elif side == b"R":
            # R x는 열 n-x+1부터 양수가 되므로
            # max(0, j - (n-x)) 형태로 저장한다.
            right_starts.append(n - x)
        else:  # side == b"D"
            vertical_range += min(x, n - 1)

    def horizontal_value(pos):
        total = 0

        for length in left_lengths:
            if length >= pos:
                total += length - pos + 1

        for start in right_starts:
            if pos >= start:
                total += pos - start

        return total

    def forward_difference(pos):
        # H(pos + 1) - H(pos)
        diff = 0

        for length in left_lengths:
            if length >= pos:
                diff -= 1

        for start in right_starts:
            if pos >= start:
                diff += 1

        return diff

    # H(j+1)-H(j) >= 0 이 처음 성립하는 j를 이분 탐색한다.
    # 그런 j가 없으면 H(n)이 최솟값이다.
    min_position = n
    lo = 1
    hi = n - 1

    while lo <= hi:
        mid = (lo + hi) // 2

        if forward_difference(mid) >= 0:
            min_position = mid
            hi = mid - 1
        else:
            lo = mid + 1

    horizontal_min = horizontal_value(min_position)
    horizontal_max = max(horizontal_value(1), horizontal_value(n))

    answer = vertical_range + horizontal_max - horizontal_min
    print(answer)


if __name__ == "__main__":
    main()