import sys
from bisect import bisect_right


def main():
    input = sys.stdin.buffer.readline

    n, m, k = map(int, input().split())
    friends = list(map(int, input().split()))
    friends.sort()

    above = [0] * m
    answer = 0

    # k = 1인 경우는 각 빈 좌석을 독립적으로 판정할 수 있다.
    if k == 1:
        friend_height = friends[0]

        for _ in range(n):
            row = list(map(int, input().split()))

            for j in range(m):
                value = row[j]

                if value == 0:
                    if friend_height > above[j]:
                        answer += 1
                else:
                    if value > above[j]:
                        above[j] = value

        print(answer)
        return

    # 각 필드의 최상위 비트보다 k가 작아야 한다.
    # k <= 127이면 8비트 필드, 그 외에는 16비트 필드를 사용한다.
    if k <= 127:
        field_bytes = 1
        field_bits = 8
        bias = 128
        high_pattern = b"\x80"
    else:
        field_bytes = 2
        field_bits = 16
        bias = 32768
        high_pattern = b"\x00\x80"

    high_mask = int.from_bytes(high_pattern * k, "little")

    # suffix[p] :
    # p번째 필드부터 마지막 필드까지 각 필드의 최하위 비트가 1인 마스크
    suffix = [0] * (k + 1)
    mask = 0
    shift = field_bits * (k - 1)

    p = k - 1
    while p >= 0:
        mask |= 1 << shift
        suffix[p] = mask
        shift -= field_bits
        p -= 1

    for _ in range(n):
        row = list(map(int, input().split()))
        rank = [0] * m

        # 현재 행의 좌석 정보를 만들고,
        # 이후 행을 위해 열별 최대 키를 갱신한다.
        for j in range(m):
            value = row[j]

            if value == 0:
                rank[j] = bisect_right(friends, above[j])
            else:
                rank[j] = k
                if value > above[j]:
                    above[j] = value

        start = 0

        while start < m:
            # rank == k인 좌석은 사용할 수 없으므로 건너뛴다.
            if rank[start] >= k:
                start += 1
                continue

            end = start + 1
            low = rank[start]
            high = rank[start]

            while end < m and rank[end] < k:
                value = rank[end]

                if value < low:
                    low = value
                elif value > high:
                    high = value

                end += 1

            length = end - start

            if length >= k:
                window_count = length - k + 1

                # 모든 좌석의 rank가 같은 경우
                if low == high:
                    if low == 0:
                        answer += window_count
                else:
                    frequency = [0] * k

                    pos = start
                    first_end = start + k

                    while pos < first_end:
                        frequency[rank[pos]] += 1
                        pos += 1

                    # 윈도우가 정확히 하나뿐이면 직접 판정
                    if length == k:
                        prefix = 0
                        valid = True
                        t = 0

                        while t < k:
                            prefix += 1 - frequency[t]

                            if prefix > 0:
                                valid = False
                                break

                            t += 1

                        answer += valid
                    else:
                        # packed의 t번째 필드에는
                        # bias + C_t 를 저장한다.
                        packed_bytes = bytearray(field_bytes * k)
                        prefix_count = 0
                        t = 0

                        if field_bytes == 1:
                            while t < k:
                                prefix_count += frequency[t]
                                field_value = bias + prefix_count - t - 1
                                packed_bytes[t] = field_value
                                t += 1
                        else:
                            while t < k:
                                prefix_count += frequency[t]
                                field_value = bias + prefix_count - t - 1
                                offset = t << 1
                                packed_bytes[offset] = field_value & 255
                                packed_bytes[offset + 1] = field_value >> 8
                                t += 1

                        packed = int.from_bytes(packed_bytes, "little")

                        valid = (packed & high_mask) == high_mask
                        answer += valid

                        pos = start + 1
                        last_start = end - k

                        while pos <= last_start:
                            outgoing = rank[pos - 1]
                            incoming = rank[pos + k - 1]

                            if outgoing != incoming:
                                if outgoing < incoming:
                                    # [outgoing, incoming) 범위의 C_t 감소
                                    packed -= (
                                        suffix[outgoing] ^ suffix[incoming]
                                    )
                                else:
                                    # [incoming, outgoing) 범위의 C_t 증가
                                    packed += (
                                        suffix[incoming] ^ suffix[outgoing]
                                    )

                                valid = (packed & high_mask) == high_mask

                            answer += valid
                            pos += 1

            start = end

    print(answer)


if __name__ == "__main__":
    main()