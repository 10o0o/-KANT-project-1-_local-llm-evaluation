import sys


def solve():
    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    n = data[0]
    k = data[1]

    if n == 1:
        sys.stdout.write("0")
        return

    parent = [-1] * n
    depth = [0] * n
    first_child = [-1] * n
    next_sibling = [-1] * n

    idx = 2
    for v in range(1, n):
        p = data[idx] - 1
        idx += 1

        parent[v] = p
        depth[v] = depth[p] + 1

        next_sibling[v] = first_child[p]
        first_child[p] = v

    z = [0] * n
    for v in range(1, n):
        z[v] = data[idx]
        idx += 1

    prefix_speed = [0] * n
    slope = [0] * n
    intercept = [0] * n

    for v in range(1, n):
        p = parent[v]
        b = data[idx]
        idx += 1

        prefix_speed[v] = prefix_speed[p] + b
        zv = z[v]

        slope[v] = -prefix_speed[p]
        intercept[v] = zv * zv

    del data

    # DFS 시간축에서의 질의값과 기본값
    total_queries = n - 1
    query_x = []
    base_value = []

    # 각 간선의 활성 구간을 [l, r, l, r, ...] 형태로 저장
    intervals = [None] * n
    active_start = [-1] * n
    expired_edge = [-1] * n

    path_edges = []
    stack = []

    child = first_child[0]
    while child != -1:
        stack.append(child)
        child = next_sibling[child]

    current_time = 0

    while stack:
        event = stack.pop()

        if event >= 0:
            v = event
            path_edges.append(v)

            d = depth[v]
            if d > k:
                old_edge = path_edges[d - k - 1]

                start = active_start[old_edge]
                if start >= 0:
                    if start < current_time:
                        arr = intervals[old_edge]
                        if arr is None:
                            intervals[old_edge] = [start, current_time - 1]
                        else:
                            arr.append(start)
                            arr.append(current_time - 1)
                    active_start[old_edge] = -1
            else:
                old_edge = -1

            expired_edge[v] = old_edge
            active_start[v] = current_time

            zv = z[v]
            query_x.append(zv)
            base_value.append(intercept[v] + zv * prefix_speed[v])
            current_time += 1

            # 종료 이벤트
            stack.append(~v)

            child = first_child[v]
            while child != -1:
                stack.append(child)
                child = next_sibling[child]

        else:
            v = ~event

            start = active_start[v]
            if start >= 0:
                if start < current_time:
                    arr = intervals[v]
                    if arr is None:
                        intervals[v] = [start, current_time - 1]
                    else:
                        arr.append(start)
                        arr.append(current_time - 1)
                active_start[v] = -1

            old_edge = expired_edge[v]
            if old_edge != -1:
                active_start[old_edge] = current_time

            path_edges.pop()

    # DFS 구조에 필요한 배열은 더 이상 필요 없음
    del parent, depth, first_child, next_sibling
    del active_start, expired_edge, path_edges
    del z, prefix_speed

    # 시간 세그먼트 트리
    size = 1
    while size < total_queries:
        size <<= 1

    events = [None] * (size << 1)

    # 직선들을 기울기 순으로 처리하면 각 이벤트 노드의 목록도 기울기 순이 된다.
    line_order = list(range(1, n))
    line_order.sort(key=slope.__getitem__)

    for line_id in line_order:
        arr = intervals[line_id]
        if arr is None:
            continue

        j = 0
        arr_len = len(arr)

        while j < arr_len:
            left = arr[j] + size
            right = arr[j + 1] + size + 1
            j += 2

            while left < right:
                if left & 1:
                    current = events[left]
                    if current is None:
                        events[left] = [line_id]
                    else:
                        current.append(line_id)
                    left += 1

                if right & 1:
                    right -= 1
                    current = events[right]
                    if current is None:
                        events[right] = [line_id]
                    else:
                        current.append(line_id)

                left >>= 1
                right >>= 1

    del intervals, line_order

    # 각 이벤트 노드의 upper convex hull 구성
    for node in range(1, len(events)):
        hull = events[node]
        if hull is None:
            continue

        original_len = len(hull)
        write = 0
        read = 0

        while read < original_len:
            line_id = hull[read]
            read += 1

            # 같은 기울기에서는 절편이 가장 큰 직선만 유지
            if write > 0:
                last_id = hull[write - 1]
                if slope[last_id] == slope[line_id]:
                    if intercept[line_id] > intercept[last_id]:
                        write -= 1
                    else:
                        continue

            # 가운데 직선이 절대 최댓값이 될 수 있으면 제거
            while write >= 2:
                first_id = hull[write - 2]
                second_id = hull[write - 1]

                left_cross = (
                    (intercept[first_id] - intercept[second_id])
                    * (slope[line_id] - slope[second_id])
                )
                right_cross = (
                    (intercept[second_id] - intercept[line_id])
                    * (slope[second_id] - slope[first_id])
                )

                if left_cross >= right_cross:
                    write -= 1
                else:
                    break

            hull[write] = line_id
            write += 1

        if write < original_len:
            del hull[write:]

    # z값 오름차순으로 질의 처리
    query_order = list(range(total_queries))
    query_order.sort(key=query_x.__getitem__)

    pointer = [0] * (size << 1)
    negative_infinity = -10**30

    for t in query_order:
        x = query_x[t]
        best_line_value = negative_infinity

        node = t + size
        while node:
            hull = events[node]

            if hull is not None:
                pos = pointer[node]
                last_pos = len(hull) - 1

                while pos < last_pos:
                    current_id = hull[pos]
                    next_id = hull[pos + 1]

                    current_value = slope[current_id] * x + intercept[current_id]
                    next_value = slope[next_id] * x + intercept[next_id]

                    if next_value >= current_value:
                        pos += 1
                    else:
                        break

                pointer[node] = pos
                line_id = hull[pos]
                value = slope[line_id] * x + intercept[line_id]

                if value > best_line_value:
                    best_line_value = value

            node >>= 1

        base_value[t] += best_line_value

    sys.stdout.write(str(max(base_value)))


if __name__ == "__main__":
    solve()