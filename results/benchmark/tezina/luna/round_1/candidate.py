import sys


def solve():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    n, k = data[0], data[1]
    arr = data[2:2 + n]

    max_a = max(arr)
    cap = 100_000_000

    frequency = [0] * (max_a + 1)
    for value in arr:
        frequency[value] += 1

    prefix_count = [0] * (max_a + 1)
    prefix_sum = [0] * (max_a + 1)

    count_acc = 0
    sum_acc = 0
    for value in range(1, max_a + 1):
        count_acc += frequency[value]
        sum_acc += frequency[value] * value
        prefix_count[value] = count_acc
        prefix_sum[value] = sum_acc

    # q(a + 2) <= cap 을 만족하는 a의 최댓값
    uncapped_until = [0] * (max_a + 1)
    for q in range(1, max_a + 1):
        uncapped_until[q] = cap // q - 2

    answer = 0
    divisor_limit = min(k, max_a)

    for divisor in range(1, divisor_limit + 1):
        quotient_limit = max_a // divisor

        for quotient in range(1, quotient_limit + 1):
            left = quotient * divisor
            right = min(max_a, left + divisor - 1)

            threshold = uncapped_until[quotient]

            if threshold >= right:
                count = prefix_count[right] - prefix_count[left - 1]
                weight_sum = prefix_sum[right] - prefix_sum[left - 1]
                answer += quotient * (weight_sum + 2 * count)

            elif threshold < left:
                count = prefix_count[right] - prefix_count[left - 1]
                answer += cap * count

            else:
                uncapped_count = (
                    prefix_count[threshold] - prefix_count[left - 1]
                )
                uncapped_sum = (
                    prefix_sum[threshold] - prefix_sum[left - 1]
                )

                total_count = prefix_count[right] - prefix_count[left - 1]
                capped_count = total_count - uncapped_count

                answer += quotient * (uncapped_sum + 2 * uncapped_count)
                answer += cap * capped_count

    print(answer)


if __name__ == "__main__":
    solve()