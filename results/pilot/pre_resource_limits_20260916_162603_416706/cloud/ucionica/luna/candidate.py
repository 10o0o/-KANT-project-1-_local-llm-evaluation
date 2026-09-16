import sys
from bisect import bisect_right


def main():
    read = sys.stdin.buffer.readline

    n, m, k = map(int, read().split())
    heights = sorted(map(int, read().split()))

    # 현재 행보다 앞선 행에서 각 열의 최대 학생 키
    front = [-1] * m

    # front[j] 이하인 친구 수
    ranks = [0] * m
    upper_bound = bisect_right

    answer = 0

    # k = 1이면 각 빈 좌석을 독립적으로 확인하면 된다.
    if k == 1:
        for _ in range(n):
            row = list(map(int, read().split()))

            j = 0
            while j < m:
                value = row[j]

                if value == 0:
                    if ranks[j] == 0:
                        answer += 1
                elif value > front[j]:
                    front[j] = value
                    ranks[j] = upper_bound(heights, value)

                j += 1

        print(answer)
        return

    size = 1
    while size < k:
        size <<= 1

    NEGATIVE_INF = -10**18

    def count_run(values, start, end):
        """values[start:end]는 모두 빈 좌석이며, 가능한 윈도우 수를 센다."""
        K = k
        S = size

        # 첫 번째 윈도우의 p 값 빈도
        frequency = [0] * (K + 1)
        pos = start
        first_end = start + K

        while pos < first_end:
            frequency[values[pos]] += 1
            pos += 1

        # 윈도우가 하나뿐이면 segment tree 없이 바로 검사
        if end - start == K:
            suffix_count = 0
            x = K

            while x > 0:
                suffix_count += frequency[x]
                if x + suffix_count > K:
                    return 0
                x -= 1

            return 1

        # segment tree의 리프:
        # leaf[x - 1] = x + (현재 윈도우에서 p >= x인 개수)
        tree = [NEGATIVE_INF] * (2 * S)

        suffix_count = 0
        x = K
        while x > 0:
            suffix_count += frequency[x]
            tree[S + x - 1] = x + suffix_count
            x -= 1

        # 초기 트리 구성
        node = S - 1
        while node > 0:
            left_value = tree[node << 1]
            right_value = tree[(node << 1) | 1]
            tree[node] = (
                left_value if left_value >= right_value else right_value
            )
            node -= 1

        # 각 노드에 lazy 값을 저장한다.
        # 부모의 lazy는 트리 값을 다시 계산할 때 더해 주므로 push가 필요 없다.
        lazy = [0] * (2 * S)

        result = 1 if tree[1] <= K else 0

        pos = start + K
        while pos < end:
            old_value = values[pos - K]
            new_value = values[pos]

            if old_value != new_value:
                if old_value < new_value:
                    left = old_value
                    right = new_value
                    delta = 1
                else:
                    left = new_value
                    right = old_value
                    delta = -1

                # [left, right) 구간에 delta 더하기
                l = left + S
                r = right + S

                first_leaf = l
                last_leaf = r - 1

                while l < r:
                    if l & 1:
                        tree[l] += delta
                        lazy[l] += delta
                        l += 1

                    if r & 1:
                        r -= 1
                        tree[r] += delta
                        lazy[r] += delta

                    l >>= 1
                    r >>= 1

                # 변경된 양 끝 경로를 다시 계산
                p = first_leaf >> 1
                q = last_leaf >> 1

                while p:
                    left_value = tree[p << 1]
                    right_value = tree[(p << 1) | 1]
                    tree[p] = lazy[p] + (
                        left_value if left_value >= right_value else right_value
                    )

                    if q != p:
                        left_value = tree[q << 1]
                        right_value = tree[(q << 1) | 1]
                        tree[q] = lazy[q] + (
                            left_value
                            if left_value >= right_value
                            else right_value
                        )

                    p >>= 1
                    q >>= 1

            if tree[1] <= K:
                result += 1

            pos += 1

        return result

    for _ in range(n):
        row = list(map(int, read().split()))
        p_values = [-1] * m

        # 현재 행을 기준으로 p 값을 계산하고,
        # 현재 행의 학생들을 다음 행을 위해 front에 반영한다.
        j = 0
        while j < m:
            value = row[j]

            if value == 0:
                p_values[j] = ranks[j]
            elif value > front[j]:
                front[j] = value
                ranks[j] = upper_bound(heights, value)

            j += 1

        # 연속된 빈 좌석 구간별로 처리
        start = 0
        while start < m:
            if p_values[start] < 0:
                start += 1
                continue

            end = start + 1
            while end < m and p_values[end] >= 0:
                end += 1

            if end - start >= k:
                answer += count_run(p_values, start, end)

            start = end

    print(answer)


if __name__ == "__main__":
    main()