import sys
from bisect import bisect_right


def solve():
    rd = sys.stdin.buffer.readline

    first = rd().split()
    if not first:
        return

    n, m, k = map(int, first)
    friends = list(map(int, rd().split()))
    friends.sort()

    front = [0] * m
    rank = [0] * m

    # k = 1인 경우
    if k == 1:
        answer = 0
        friend_height = friends[0]

        for _ in range(n):
            values = list(map(int, rd().split()))

            for j, value in enumerate(values):
                current_rank = rank[j]

                if value == 0:
                    if current_rank == 0:
                        answer += 1
                elif value > front[j]:
                    front[j] = value
                    rank[j] = 1 if value >= friend_height else 0

        print(answer)
        return

    # 세그먼트 트리는 x = 1 .. k-1을 관리한다.
    # rank == k인 좌석은 사용할 수 없으므로 연속 구간에서 제외한다.
    limit = k - 1

    size = 1
    while size < limit:
        size <<= 1

    # 각 q에 대해 [1, q] prefix를 이루는 canonical node들과
    # 갱신 후 다시 계산해야 하는 조상들을 미리 저장한다.
    covers = [None] * (limit + 1)
    ancestors = [None] * (limit + 1)

    for q in range(1, limit + 1):
        if q == size:
            covers[q] = (1,)
            ancestors[q] = ()
            continue

        node = 1
        lo = 1
        hi = size
        nodes = []

        while lo < hi:
            mid = (lo + hi) >> 1

            if q <= mid:
                node <<= 1
                hi = mid
            else:
                nodes.append(node << 1)
                node = (node << 1) | 1
                lo = mid + 1

        nodes.append(node)
        covers[q] = tuple(nodes)

        path = []
        node >>= 1
        while node:
            path.append(node)
            node >>= 1
        ancestors[q] = tuple(path)

    answer = 0
    negative_infinity = -10**9

    # 연속된 완전 빈 행은 앞쪽 학생 정보가 변하지 않으므로
    # 같은 결과를 재사용할 수 있다.
    previous_row_was_all_empty = False
    previous_row_count = 0

    for _ in range(n):
        values = list(map(int, rd().split()))

        # 현재 행에서 사용할 rank는 행 처리 전의 값이어야 한다.
        required = rank.copy()
        usable = bytearray(m)
        all_empty = True

        for j, value in enumerate(values):
            q = required[j]

            if value == 0:
                if q < k:
                    usable[j] = 1
            else:
                all_empty = False

                # 현재 행의 학생은 현재 행의 친구들 앞에 있지 않으므로,
                # 다음 행부터 front에 반영한다.
                if value > front[j]:
                    front[j] = value
                    rank[j] = bisect_right(friends, value)

        if all_empty and previous_row_was_all_empty:
            answer += previous_row_count
            continue

        row_count = 0

        start = usable.find(b"\x01")

        while start != -1:
            end = usable.find(b"\x00", start)
            if end == -1:
                end = m

            run_length = end - start

            if run_length >= k:
                # 첫 번째 윈도우의 rank 빈도 계산
                frequency = [0] * k

                for pos in range(start, start + k):
                    frequency[required[pos]] += 1

                tree = [negative_infinity] * (size << 1)
                lazy = [0] * (size << 1)

                # tree[x] = x + 현재 윈도우에서 rank >= x인 좌석 수
                suffix_count = 0
                for x in range(limit, 0, -1):
                    suffix_count += frequency[x]
                    tree[size + x - 1] = x + suffix_count

                for node in range(size - 1, 0, -1):
                    left = tree[node << 1]
                    right = tree[(node << 1) | 1]
                    tree[node] = left if left > right else right

                valid = tree[1] <= k
                if valid:
                    row_count += 1

                pos = start + k

                while pos < end:
                    outgoing = required[pos - k]
                    incoming = required[pos]

                    if outgoing != incoming:
                        if outgoing:
                            for node in covers[outgoing]:
                                tree[node] -= 1
                                lazy[node] -= 1

                            for node in ancestors[outgoing]:
                                child = node << 1
                                left = tree[child]
                                right = tree[child | 1]
                                tree[node] = lazy[node] + (
                                    left if left > right else right
                                )

                        if incoming:
                            for node in covers[incoming]:
                                tree[node] += 1
                                lazy[node] += 1

                            for node in ancestors[incoming]:
                                child = node << 1
                                left = tree[child]
                                right = tree[child | 1]
                                tree[node] = lazy[node] + (
                                    left if left > right else right
                                )

                        valid = tree[1] <= k

                    if valid:
                        row_count += 1

                    pos += 1

            start = usable.find(b"\x01", end)

        answer += row_count
        previous_row_count = row_count
        previous_row_was_all_empty = all_empty

    print(answer)


if __name__ == "__main__":
    solve()