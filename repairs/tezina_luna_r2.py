import sys


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    n, k = data[0], data[1]
    arr = data[2:2 + n]

    max_a = max(arr)

    freq = [0] * (max_a + 1)
    for x in arr:
        freq[x] += 1

    prefix_count = [0] * (max_a + 1)
    prefix_sum = [0] * (max_a + 1)

    count_so_far = 0
    sum_so_far = 0

    for value in range(1, max_a + 1):
        count_so_far += freq[value]
        sum_so_far += freq[value] * value
        prefix_count[value] = count_so_far
        prefix_sum[value] = sum_so_far

    CAP = 100_000_000
    answer = 0

    for d in range(1, min(k, max_a) + 1):
        left = d

        while left <= max_a:
            q = left // d
            right = min(max_a, (q + 1) * d - 1)

            # q * (a + 2) <= CAP 인 최대 a
            uncapped_right = CAP // q - 2
            uncapped_right = min(right, uncapped_right)

            if uncapped_right >= left:
                cnt = (
                    prefix_count[uncapped_right]
                    - prefix_count[left - 1]
                )
                total_weight = (
                    prefix_sum[uncapped_right]
                    - prefix_sum[left - 1]
                )
                answer += q * (total_weight + 2 * cnt)

            capped_left = max(left, uncapped_right + 1)
            if capped_left <= right:
                cnt = prefix_count[right] - prefix_count[capped_left - 1]
                answer += CAP * cnt

            left = right + 1

    print(answer)


if __name__ == "__main__":
    main()