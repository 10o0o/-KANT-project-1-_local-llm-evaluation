import sys


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    n, k = data[0], data[1]
    values = data[2:2 + n]

    max_a = max(values)

    frequency = [0] * (max_a + 1)
    for value in values:
        frequency[value] += 1

    # j > max_a이면 floor(a / j) = 0이므로 고려할 필요가 없다.
    divisor_limit = min(k, max_a)

    # divisor_count[x] = x의 약수 중 divisor_limit 이하인 약수의 개수
    divisor_count = [0] * (max_a + 1)
    for divisor in range(1, divisor_limit + 1):
        for multiple in range(divisor, max_a + 1, divisor):
            divisor_count[multiple] += 1

    cap = 100_000_000
    prefix_divisors = 0
    answer = 0

    for a in range(1, max_a + 1):
        prefix_divisors += divisor_count[a]

        count = frequency[a]
        if count == 0:
            continue

        multiplier = a + 2

        # 상한을 적용하지 않은 합
        uncapped = multiplier * prefix_divisors

        # 상한이 적용되는 j의 마지막 값
        threshold = cap // multiplier
        limit = a // (threshold + 1)
        if limit > k:
            limit = k

        # 상한을 적용하면서 줄어드는 초과분
        excess = 0
        for j in range(1, limit + 1):
            excess += multiplier * (a // j) - cap

        contribution = uncapped - excess
        answer += count * contribution

    print(answer)


if __name__ == "__main__":
    main()