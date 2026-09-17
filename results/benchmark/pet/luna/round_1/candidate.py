import sys


def main():
    rd = sys.stdin.buffer.readline
    first = rd().split()
    if not first:
        return

    n, m = map(int, first)

    # 행을 8의 배수 길이 비트마스크로 저장한다.
    width = (m + 7) // 8 * 8
    padding = b"0" * (width - m)

    row_masks = []
    row_h = []

    # col_count[j] = c_j
    # q[j] = Q_j = sum of h_i over water lilies in column j
    col_count = [0] * m
    q = [0] * m

    for _ in range(n):
        s = rd().strip()
        ones = s.count(b"1")
        h = ones - 1

        row_h.append(h)
        row_masks.append(int(s + padding, 2))

        for j, ch in enumerate(s):
            if ch == 49:  # '1'
                col_count[j] += 1
                q[j] += h

    # v_j = c_j - 1
    col_v = [x - 1 for x in col_count]

    # 패딩 위치는 실제 열이 아니므로 합에 영향을 주지 않도록 0을 넣는다.
    col_v_ext = col_v + [0] * (width - m)
    q_ext = q + [0] * (width - m)

    # 각 행에 대해 P_i와 U_i를 8개 열 단위 lookup으로 계산한다.
    blocks = width // 8
    p_table = []
    u_table = []

    for block in range(blocks):
        base = block * 8
        pt = [0] * 256
        ut = [0] * 256

        for pattern in range(1, 256):
            low = pattern & -pattern
            offset = 7 - (low.bit_length() - 1)
            previous = pattern ^ low

            pt[pattern] = pt[previous] + col_v_ext[base + offset]
            ut[pattern] = ut[previous] + q_ext[base + offset]

        p_table.append(pt)
        u_table.append(ut)

    p = [0] * n  # P_i
    u = [0] * n  # U_i

    for i, mask in enumerate(row_masks):
        pi = 0
        ui = 0
        shift = width - 8

        for block in range(blocks):
            pattern = (mask >> shift) & 255
            pi += p_table[block][pattern]
            ui += u_table[block][pattern]
            shift -= 8

        p[i] = pi
        u[i] = ui

    # T = 2X - row_penalty - col_penalty
    x = 0
    row_penalty = 0

    for i in range(n):
        h = row_h[i]
        pi = p[i]

        x += pi * u[i]
        # h^2 + r_i*h = h^2 + (h+1)h = 2h^2 + h
        row_penalty += pi * (2 * h * h + h)

    col_penalty = 0
    for j in range(m):
        v = col_v[j]
        col_penalty += q[j] * (2 * v * v + v)

    total = 2 * x - row_penalty - col_penalty

    # 직사각형 개수 계산
    try:
        bit_count = int.bit_count
    except AttributeError:
        bit_count = lambda value: bin(value).count("1")

    active_rows = [mask for mask in row_masks if bit_count(mask) >= 2]

    rectangles = 0
    for i in range(1, len(active_rows)):
        current = active_rows[i]
        for j in range(i):
            common = bit_count(current & active_rows[j])
            rectangles += common * (common - 1) // 2

    answer = total - 8 * rectangles
    sys.stdout.write(str(answer) + "\n")


if __name__ == "__main__":
    main()