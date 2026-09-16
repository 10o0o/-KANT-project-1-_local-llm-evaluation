import sys


def main():
    rd = sys.stdin.buffer.readline
    n, m = map(int, rd().split())

    row_masks = [0] * n
    row_deg = [0] * n
    col_deg = [0] * m

    # A_j = sum of (R_i - 1) over all lilies in column j
    col_a = [0] * m

    for i in range(n):
        line = rd().strip()

        # Make bit j correspond to the original column j.
        mask = int(line[::-1], 2)
        row_masks[i] = mask

        r = mask.bit_count()
        row_deg[i] = r
        add = r - 1

        for j, ch in enumerate(line):
            if ch == 49:  # ord('1')
                col_deg[j] += 1
                col_a[j] += add

    # sum_j A_j * C_j * (C_j - 1)
    constant = 0
    for j in range(m):
        c = col_deg[j]
        constant += col_a[j] * c * (c - 1)

    # Pack (C_j - 1) and A_j into one integer.
    # The low bits store U_i, and the high bits store W_i.
    # U_i <= m * (n - 1), so this field is sufficiently wide.
    shift = (m * (n - 1)).bit_length() + 1
    low_mask = (1 << shift) - 1

    packed_weight = [0] * m
    for j, c in enumerate(col_deg):
        if c != 0:
            # Empty columns never occur in a row mask.
            packed_weight[j] = (c - 1) + (col_a[j] << shift)

    # Lookup table for every 8-column pattern.
    block_count = (m + 7) // 8
    lookup = []

    for start in range(0, m, 8):
        values = packed_weight[start:start + 8]
        if len(values) < 8:
            values += [0] * (8 - len(values))

        table = [0] * 256
        for pattern in range(1, 256):
            bit = pattern & -pattern
            table[pattern] = (
                table[pattern ^ bit] + values[bit.bit_length() - 1]
            )
        lookup.append(table)

    # Count all H-V-H-V walks, before removing paths returning to start.
    raw_h = -constant

    for i, mask in enumerate(row_masks):
        packed = 0
        row_bytes = mask.to_bytes(block_count, "little")

        for k, value in enumerate(row_bytes):
            packed += lookup[k][value]

        u = packed & low_mask       # U_i
        w = packed >> shift         # W_i

        q = row_deg[i] - 1
        raw_h += u * (w - q * q)

    # Count all-ones rectangles.
    # Grouping identical row masks reduces work on repetitive grids.
    frequency = {}
    for mask, r in zip(row_masks, row_deg):
        if r >= 2:
            frequency[mask] = frequency.get(mask, 0) + 1

    items = list(frequency.items())
    rectangles = 0

    # Pairs of identical rows
    for mask, count in items:
        if count >= 2:
            common = mask.bit_count()
            rectangles += (
                (count * (count - 1) // 2)
                * (common * (common - 1) // 2)
            )

    # Pairs of different row masks
    for i in range(1, len(items)):
        x, fx = items[i]
        for y, fy in items[:i]:
            common = (x & y).bit_count()
            rectangles += fx * fy * (common * (common - 1) // 2)

    answer = 2 * (raw_h - 4 * rectangles)
    print(answer)


if __name__ == "__main__":
    main()