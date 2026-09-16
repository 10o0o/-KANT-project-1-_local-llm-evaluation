import sys

def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    n, k = data[0], data[1]
    arr = data[2:2 + n]

    max_a = max(arr)
    cap = 100_000_000

    freq = [0] * (max_a + 1)
    for x in arr:
        freq[x] += 1

    prefix_count = [0] * (max_a + 1)
    prefix_value = [0] * (max_a + 1)

    for x in range(1, max_a + 1):
        prefix_count[x] = prefix_count[x - 1] + freq[x]
        prefix_value[x] = (
            prefix_value[x - 1] + freq[x] * (x + 2)
        )

    answer = 0
    limit_d = min(k, max_a)

    for d in range(1, limit_d + 1):
        max_q = max_a // d

        for q in range(1, max_q + 1):
            left = q * d
            right = min(max_a, (q + 1) * d - 1)

            threshold = cap // q - 2
            uncapped_right = min(right, threshold)

            if uncapped_right >= left:
                value_sum = (
                    prefix_value[uncapped_right]
                    - prefix_value[left - 1]
                )
                answer += q * value_sum

                capped_left = uncapped_right + 1
            else:
                capped_left = left

            if capped_left <= right:
                count = (
                    prefix_count[right]
                    - prefix_count[capped_left - 1]
                )
                answer += cap * count

    print(answer)

if __name__ == "__main__":
    main()