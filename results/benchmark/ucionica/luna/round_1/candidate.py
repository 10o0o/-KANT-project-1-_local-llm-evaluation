import sys
from bisect import bisect_right


def main():
    read = sys.stdin.buffer.readline

    n, m, k = map(int, read().split())
    heights = sorted(map(int, read().split()))

    # need[j]:
    # 현재 행에서 j열의 빈 좌석에 필요한 가장 작은 친구 인덱스
    need = [1] * m

    # k = 1이면 각 빈 좌석을 독립적으로 판단할 수 있다.
    if k == 1:
        friend_height = heights[0]
        answer = 0

        for _ in range(n):
            row = list(map(int, read().split()))

            for j in range(m):
                value = row[j]

                if value == 0:
                    if need[j] == 1:
                        answer += 1
                else:
                    # 현재 학생은 다음 행부터 영향을 준다.
                    if need[j] == 1 and value >= friend_height:
                        need[j] = 2

        print(answer)
        return

    # 세그먼트 트리는 q = 1 .. k-1만 관리한다.
    length = k - 1
    size = 1
    while size < length:
        size <<= 1

    total = size << 1
    INF = 10**9

    # 각 리프의 기본값은 cnt[q] - 1 = -1
    # 실제 구간 밖의 리프는 INF로 둔다.
    base_sum = [0] * total
    base_min = [INF] * total

    for i in range(length):
        idx = size + i
        base_sum[idx] = -1
        base_min[idx] = -1

    for node in range(size - 1, 0, -1):
        left = node << 1
        left_sum = base_sum[left]

        base_sum[node] = left_sum + base_sum[left | 1]

        a = base_min[left]
        b = left_sum + base_min[left | 1]
        base_min[node] = a if a < b else b

    seg_sum = base_sum.copy()
    seg_min = base_min.copy()

    # 현재 행의 빈 구간에서 각 칸의 요구 인덱스
    values = [0] * m

    impossible_value = k + 1
    answer = 0
    upper_bound = bisect_right

    for _ in range(n):
        row = list(map(int, read().split()))
        run = 0

        for j in range(m):
            value = row[j]

            if value == 0:
                p = need[j]
                values[j] = p
                run += 1

                # 아직 길이 k인 윈도우가 만들어지지 않았다.
                if run < k:
                    continue

                if run == k:
                    # 새로운 빈 구간의 첫 윈도우를 직접 구성한다.
                    seg_sum[:] = base_sum
                    seg_min[:] = base_min

                    bad = 0
                    start = j - k + 1

                    for t in range(start, j + 1):
                        requirement = values[t]

                        if requirement == impossible_value:
                            bad += 1
                        elif requirement < k:
                            leaf = size + requirement - 1
                            seg_sum[leaf] += 1
                            seg_min[leaf] += 1

                    for node in range(size - 1, 0, -1):
                        left = node << 1
                        left_sum = seg_sum[left]

                        seg_sum[node] = left_sum + seg_sum[left | 1]

                        a = seg_min[left]
                        b = left_sum + seg_min[left | 1]
                        seg_min[node] = a if a < b else b

                    if bad == 0 and seg_min[1] >= 0:
                        answer += 1

                else:
                    # 윈도우가 한 칸 이동한다.
                    old = values[j - k]

                    if p != old:
                        if p == impossible_value:
                            bad += 1
                        if old == impossible_value:
                            bad -= 1

                        # 두 요구 인덱스가 모두 세그먼트 트리에 포함되는 경우
                        if p < k and old < k:
                            x = size + p - 1
                            y = size + old - 1

                            seg_sum[x] += 1
                            seg_min[x] = seg_sum[x]

                            seg_sum[y] -= 1
                            seg_min[y] = seg_sum[y]

                            x >>= 1
                            y >>= 1

                            # 두 경로가 합쳐지기 전까지 각각 갱신
                            while x != y:
                                left = x << 1
                                left_sum = seg_sum[left]
                                seg_sum[x] = left_sum + seg_sum[left | 1]

                                a = seg_min[left]
                                b = left_sum + seg_min[left | 1]
                                seg_min[x] = a if a < b else b

                                left = y << 1
                                left_sum = seg_sum[left]
                                seg_sum[y] = left_sum + seg_sum[left | 1]

                                a = seg_min[left]
                                b = left_sum + seg_min[left | 1]
                                seg_min[y] = a if a < b else b

                                x >>= 1
                                y >>= 1

                            # 공통 경로 갱신
                            while x:
                                left = x << 1
                                left_sum = seg_sum[left]
                                seg_sum[x] = left_sum + seg_sum[left | 1]

                                a = seg_min[left]
                                b = left_sum + seg_min[left | 1]
                                seg_min[x] = a if a < b else b

                                x >>= 1

                        else:
                            # 세그먼트 트리에 반영할 점 갱신이 하나인 경우
                            if p < k:
                                x = size + p - 1
                                delta = 1
                            elif old < k:
                                x = size + old - 1
                                delta = -1
                            else:
                                x = 0
                                delta = 0

                            if delta:
                                seg_sum[x] += delta
                                seg_min[x] = seg_sum[x]

                                x >>= 1
                                while x:
                                    left = x << 1
                                    left_sum = seg_sum[left]
                                    seg_sum[x] = left_sum + seg_sum[left | 1]

                                    a = seg_min[left]
                                    b = left_sum + seg_min[left | 1]
                                    seg_min[x] = a if a < b else b

                                    x >>= 1

                    if bad == 0 and seg_min[1] >= 0:
                        answer += 1

            else:
                # 빈 구간이 끊긴다.
                run = 0

                # need[j] == k+1이면 이미 어떤 친구도 볼 수 없으므로
                # 이후 더 큰 학생을 확인할 필요가 없다.
                if need[j] != impossible_value:
                    requirement = upper_bound(heights, value) + 1
                    if requirement > need[j]:
                        need[j] = requirement

    print(answer)


if __name__ == "__main__":
    main()