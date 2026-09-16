import sys


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return

    n = int(data[0])
    m = int(data[1])
    grid = data[2:2 + n]

    one = 49

    row_degree = [0] * n
    col_degree = [0] * m
    row_bits = [0] * n

    # 행별 백합 수, 열별 백합 수, 행 비트셋 계산
    for r, row in enumerate(grid):
        bits = int(row, 2)
        row_bits[r] = bits
        row_degree[r] = bits.bit_count()

        for c, ch in enumerate(row):
            if ch == one:
                col_degree[c] += 1

    a = [d - 1 for d in row_degree]
    b = [e - 1 for e in col_degree]

    # x[r] = sum of b[c] over lilies in row r
    # z[c] = sum of a[r] over lilies in column c
    x = [0] * n
    z = [0] * m

    for r, row in enumerate(grid):
        ar = a[r]
        xr = 0

        for c, ch in enumerate(row):
            if ch == one:
                xr += b[c]
                z[c] += ar

        x[r] = xr

    # y[c] = sum of x[r] over lilies in column c
    # w[r] = sum of z[c] over lilies in row r
    y = [0] * m
    w = [0] * n

    for r, row in enumerate(grid):
        xr = x[r]
        wr = 0

        for c, ch in enumerate(row):
            if ch == one:
                y[c] += xr
                wr += z[c]

        w[r] = wr

    # H -> V -> H -> V
    h_first = (
        sum(y[c] * z[c] for c in range(m))
        - sum(row_degree[r] * a[r] * x[r] for r in range(n))
        - sum(b[c] * b[c] * z[c] for c in range(m))
    )

    # V -> H -> V -> H
    v_first = (
        sum(w[r] * x[r] for r in range(n))
        - sum(col_degree[c] * b[c] * z[c] for c in range(m))
        - sum(a[r] * a[r] * x[r] for r in range(n))
    )

    # 모든 칸이 백합인 2 x 2 직사각형 개수
    # 백합이 2개 미만인 행은 직사각형에 참여할 수 없다.
    rect_rows = [
        bits
        for bits, degree in zip(row_bits, row_degree)
        if degree >= 2
    ]

    rectangles = 0

    for i, current in enumerate(rect_rows):
        for previous in rect_rows[:i]:
            common = (current & previous).bit_count()
            rectangles += common * (common - 1) // 2

    answer = h_first + v_first - 8 * rectangles
    print(answer)


if __name__ == "__main__":
    main()