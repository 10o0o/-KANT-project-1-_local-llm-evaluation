import sys


def weighted_column_sums(row_bits, weights, width):
    """
    result[j] = sum(weights[i]) over all rows i whose bit j is set.

    planes[k]의 bit j는 현재 합의 k번째 비트이다.
    비트셋 단위의 이진 덧셈을 수행한다.
    """
    planes = []

    for row_mask, value in zip(row_bits, weights):
        if row_mask == 0 or value == 0:
            continue

        while value:
            low = value & -value
            level = low.bit_length() - 1

            carry = row_mask
            while carry:
                while level >= len(planes):
                    planes.append(0)

                old = planes[level]
                planes[level] = old ^ carry
                carry = old & carry
                level += 1

            value ^= low

    result = [0] * width

    for pos in range(width):
        bit = 1 << pos
        total = 0

        for level, plane in enumerate(planes):
            if plane & bit:
                total |= 1 << level

        result[pos] = total

    return result


def make_weight_masks(weights):
    """
    masks[k]의 bit p는 weights[p]의 k번째 비트가 1인지를 나타낸다.
    """
    max_level = 0
    for value in weights:
        max_level = max(max_level, value.bit_length())

    masks = [0] * max_level

    for pos, value in enumerate(weights):
        bit = 1 << pos

        while value:
            low = value & -value
            level = low.bit_length() - 1
            masks[level] |= bit
            value ^= low

    return masks


def dot_products(row_bits, masks):
    """
    각 행에 대해, 해당 행에 포함된 위치들의 가중 합을 계산한다.
    """
    result = []

    for row_mask in row_bits:
        total = 0

        for level, mask in enumerate(masks):
            total += (row_mask & mask).bit_count() << level

        result.append(total)

    return result


def count_by_column_pairs(row_bits, width, invert):
    """
    각 행에서 열 쌍을 직접 열거하여 직사각형 수를 센다.
    invert=True이면 0인 칸들을 대상으로 센다.
    """
    full_mask = (1 << width) - 1 if invert else 0
    frequency = {}

    for row in row_bits:
        positions = []
        y = (full_mask ^ row) if invert else row

        while y:
            low = y & -y
            positions.append(low.bit_length() - 1)
            y ^= low

        length = len(positions)

        for right in range(1, length):
            right_pos = positions[right]

            for left in range(right):
                key = positions[left] * width + right_pos
                frequency[key] = frequency.get(key, 0) + 1

    answer = 0
    for count in frequency.values():
        answer += count * (count - 1) // 2

    return answer


def count_by_row_intersections(row_bits, row_counts):
    """
    행 비트셋들의 교집합 크기를 이용해 직사각형 수를 센다.
    같은 비트셋을 가진 행들은 묶어서 처리한다.
    """
    groups = {}

    for row, count in zip(row_bits, row_counts):
        if count >= 2:
            groups[row] = groups.get(row, 0) + 1

    bits = list(groups.keys())
    frequencies = [groups[x] for x in bits]

    answer = 0
    group_count = len(bits)

    for i in range(group_count):
        current = bits[i]
        current_frequency = frequencies[i]
        degree = current.bit_count()

        if current_frequency >= 2:
            answer += (
                current_frequency * (current_frequency - 1) // 2
            ) * (degree * (degree - 1) // 2)

        for j in range(i):
            common = (current & bits[j]).bit_count()

            if common >= 2:
                answer += (
                    current_frequency
                    * frequencies[j]
                    * (common * (common - 1) // 2)
                )

    return answer


def count_rectangles(row_bits, row_counts, col_counts, width):
    """
    모든 1로 이루어진 2x2 직사각형의 개수를 센다.
    """
    n = len(row_bits)
    row_pairs = n * (n - 1) // 2

    one_pair_work = sum(
        count * (count - 1) // 2 for count in row_counts
    )

    zero_counts = [width - count for count in row_counts]
    zero_pair_work = sum(
        count * (count - 1) // 2 for count in zero_counts
    )

    active_one = sum(count >= 2 for count in row_counts)
    active_zero = sum(count >= 2 for count in zero_counts)

    active_one_pairs = active_one * (active_one - 1) // 2
    active_zero_pairs = active_zero * (active_zero - 1) // 2

    LIMIT = 1_000_000

    # 희소한 1을 이용하는 방법
    if one_pair_work <= LIMIT and one_pair_work <= active_one_pairs:
        return count_by_column_pairs(row_bits, width, False)

    # 희소한 0을 이용하는 방법
    if zero_pair_work <= LIMIT and zero_pair_work <= active_zero_pairs:
        zero_rectangles = count_by_column_pairs(row_bits, width, True)

        total_zero_degree = sum(zero_counts)

        # 각 열에서 1인 행들의 zero degree 합
        ones_zero_degree = weighted_column_sums(
            row_bits, zero_counts, width
        )

        # 각 열에서 0인 행들의 zero degree 합
        zero_weight = [
            total_zero_degree - value for value in ones_zero_degree
        ]

        sum_t = 0
        sum_at = 0

        for zero_col_count, weight in zip(
            [n - value for value in col_counts],
            zero_weight
        ):
            pairs = zero_col_count * (zero_col_count - 1) // 2
            sum_t += pairs
            sum_at += width * pairs - (zero_col_count - 1) * weight

        sum_q = sum(zero_counts)
        sum_q2 = sum(value * value for value in zero_counts)

        sum_a = row_pairs * width - (n - 1) * sum_q

        sum_a2 = (
            row_pairs * width * width
            - 2 * width * (n - 1) * sum_q
            + (n - 2) * sum_q2
            + sum_q * sum_q
        )

        # x_ij = a_ij + t_ij
        # sum(t_ij^2) = sum(t_ij) + 2 * sum(C(t_ij, 2))
        sum_x2 = sum_a2 + 2 * sum_at + sum_t + 2 * zero_rectangles
        sum_x = sum_a + sum_t

        return (sum_x2 - sum_x) // 2

    # 일반적인 경우: 행 비트셋 교집합 사용
    return count_by_row_intersections(row_bits, row_counts)


def main():
    tokens = sys.stdin.buffer.read().split()

    if not tokens:
        return

    n = int(tokens[0])
    m = int(tokens[1])

    row_bits = [
        int(token, 2)
        for token in tokens[2:2 + n]
    ]

    del tokens

    row_counts = [row.bit_count() for row in row_bits]
    alpha = [
        count - 1 if count > 0 else 0
        for count in row_counts
    ]

    # 각 열의 물결잎 개수
    col_counts = weighted_column_sums(
        row_bits, [1] * n, m
    )

    beta = [
        count - 1 if count > 0 else 0
        for count in col_counts
    ]

    # Q_i = sum_j X[i][j] * beta_j
    q = dot_products(row_bits, make_weight_masks(beta))

    # P_j = sum_i X[i][j] * alpha_i
    p = weighted_column_sums(row_bits, alpha, m)

    # S_j = sum_i X[i][j] * Q_i
    s = weighted_column_sums(row_bits, q, m)

    # T_j = sum_i X[i][j] * alpha_i * Q_i
    alpha_q = [a * value for a, value in zip(alpha, q)]
    t = weighted_column_sums(row_bits, alpha_q, m)

    horizontal = 0
    for j in range(m):
        horizontal += (
            p[j] * s[j]
            - t[j]
            - p[j] * beta[j] * beta[j]
        )

    # U_i = sum_j X[i][j] * P_j
    u = dot_products(row_bits, make_weight_masks(p))

    # W_i = sum_j X[i][j] * beta_j * P_j
    beta_p = [b * value for b, value in zip(beta, p)]
    w = dot_products(row_bits, make_weight_masks(beta_p))

    vertical = 0
    for i in range(n):
        vertical += (
            q[i] * u[i]
            - w[i]
            - q[i] * alpha[i] * alpha[i]
        )

    rectangles = count_rectangles(
        row_bits, row_counts, col_counts, m
    )

    answer = horizontal + vertical - 8 * rectangles
    sys.stdout.write(str(answer) + "\n")


if __name__ == "__main__":
    main()