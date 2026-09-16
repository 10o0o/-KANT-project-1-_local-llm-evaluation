import sys
from array import array


def solve():
    rd = sys.stdin.buffer.readline

    first = rd().split()
    if not first:
        return

    n, k = map(int, first)

    parent = array('i', [0]) * (n + 1)
    values = iter(map(int, rd().split()))
    for v in range(2, n + 1):
        parent[v] = next(values)
    del values

    z = array('i', [0]) * (n + 1)
    values = iter(map(int, rd().split()))
    for v in range(2, n + 1):
        z[v] = next(values)
    del values

    speed = array('i', [0]) * (n + 1)
    values = iter(map(int, rd().split()))
    for v in range(2, n + 1):
        speed[v] = next(values)
    del values

    # 정점이 하나면 슬로프가 없다.
    if n == 1:
        sys.stdout.write("0\n")
        return

    adjacency = [[] for _ in range(n + 1)]
    for v in range(2, n + 1):
        p = parent[v]
        adjacency[p].append(v)
        adjacency[v].append(p)

    depth = array('i', [0]) * (n + 1)
    prefix = array('q', [0]) * (n + 1)
    intercept = array('q', [0]) * (n + 1)
    line_slope = array('q', [0]) * (n + 1)
    base = array('q', [0]) * (n + 1)

    # parent[i] < i 이므로 입력 순서대로 계산 가능하다.
    for v in range(2, n + 1):
        p = parent[v]
        depth[v] = depth[p] + 1
        prefix[v] = prefix[p] + speed[v]

        intercept[v] = z[v] * z[v]
        line_slope[v] = -prefix[p]
        base[v] = intercept[v] + z[v] * prefix[v]

    del speed
    del prefix

    # Euler Tour: 조상 여부 판정용
    tin = array('i', [0]) * (n + 1)
    tout = array('i', [0]) * (n + 1)

    timer = 0
    stack = [1]

    while stack:
        x = stack.pop()

        if x > 0:
            tin[x] = timer
            timer += 1

            stack.append(-x)
            px = parent[x]

            for to in reversed(adjacency[x]):
                if to != px:
                    stack.append(to)
        else:
            tout[-x] = timer

    # 모든 가능한 질의 x=z[v]를 좌표 압축
    x_values = sorted(set(z[2:]))
    x_count = len(x_values)

    x_index = {value: idx for idx, value in enumerate(x_values)}
    compressed_x = array('i', [0]) * (n + 1)

    for v in range(2, n + 1):
        compressed_x[v] = x_index[z[v]]

    del x_index

    NEG_INF = -10 ** 30

    # Li Chao Tree
    tree_size = 4 * x_count + 5
    owner = [0] * tree_size
    line_at = [-1] * tree_size

    def add_line(line_id, version,
                 owner=owner, line_at=line_at,
                 xs=x_values, ic=intercept, sl=line_slope,
                 count=x_count):
        pos = 1
        left = 0
        right = count - 1
        new_line = line_id

        while True:
            if owner[pos] != version:
                owner[pos] = version
                line_at[pos] = new_line
                return

            current_line = line_at[pos]
            mid = (left + right) >> 1
            mid_x = xs[mid]

            if (ic[new_line] + sl[new_line] * mid_x >
                    ic[current_line] + sl[current_line] * mid_x):
                line_at[pos] = new_line
                new_line = current_line

            if left == right:
                return

            stored = line_at[pos]

            if (ic[new_line] + sl[new_line] * xs[left] >
                    ic[stored] + sl[stored] * xs[left]):
                pos <<= 1
                right = mid
            elif (ic[new_line] + sl[new_line] * xs[right] >
                  ic[stored] + sl[stored] * xs[right]):
                pos = (pos << 1) | 1
                left = mid + 1
            else:
                return

    def query_line(x_pos, version,
                   owner=owner, line_at=line_at,
                   xs=x_values, ic=intercept, sl=line_slope,
                   count=x_count, neg=NEG_INF):
        pos = 1
        left = 0
        right = count - 1
        result = neg

        while owner[pos] == version:
            line_id = line_at[pos]
            value = ic[line_id] + sl[line_id] * xs[x_pos]

            if value > result:
                result = value

            if left == right:
                break

            mid = (left + right) >> 1

            if x_pos <= mid:
                pos <<= 1
                right = mid
            else:
                pos = (pos << 1) | 1
                left = mid + 1

        return result

    # 정적 직선 집합의 upper hull 구성
    def build_hull(ids, ic=intercept, sl=line_slope):
        ids.sort(key=sl.__getitem__)

        unique = []
        for line_id in ids:
            if unique and sl[line_id] == sl[unique[-1]]:
                if ic[line_id] > ic[unique[-1]]:
                    unique[-1] = line_id
            else:
                unique.append(line_id)

        hull = []

        for line_id in unique:
            while len(hull) >= 2:
                a = hull[-2]
                b = hull[-1]

                # intersection(a,b) >= intersection(b,line_id)
                # 이면 b는 upper hull에서 불필요하다.
                if ((ic[a] - ic[b]) * (sl[line_id] - sl[b]) >=
                        (ic[b] - ic[line_id]) * (sl[b] - sl[a])):
                    hull.pop()
                else:
                    break

            hull.append(line_id)

        return hull

    removed = bytearray(n + 1)
    work_parent = array('i', [0]) * (n + 1)
    subtree_size = array('i', [0]) * (n + 1)

    tasks = [1]
    version = 0
    answer = NEG_INF

    while tasks:
        start = tasks.pop()

        if removed[start]:
            continue

        # 현재 centroid component 수집
        order = [start]
        work_parent[start] = 0

        scan = 0
        while scan < len(order):
            v = order[scan]
            scan += 1

            pv = work_parent[v]

            for to in adjacency[v]:
                if not removed[to] and to != pv:
                    work_parent[to] = v
                    order.append(to)

        total = len(order)

        for v in order:
            subtree_size[v] = 1

        for idx in range(total - 1, 0, -1):
            v = order[idx]
            subtree_size[work_parent[v]] += subtree_size[v]

        # centroid 찾기
        half = total // 2
        centroid = start

        while True:
            current_size = subtree_size[centroid]
            move = 0

            for to in adjacency[centroid]:
                if removed[to]:
                    continue

                if work_parent[to] == centroid:
                    part = subtree_size[to]
                elif work_parent[centroid] == to:
                    part = total - current_size
                else:
                    continue

                if part > half:
                    move = to
                    break

            if move == 0:
                break

            centroid = move

        c = centroid

        # c의 조상들을 c에서 가까운 순서로 수집
        up_nodes = []
        u = c

        while u != 1 and not removed[u]:
            up_nodes.append(u)
            u = parent[u]

        max_up = min(len(up_nodes), k)

        if max_up:
            left_tin = tin[c]
            right_tin = tout[c]
            depth_c = depth[c]

            down_nodes = []
            max_down = -1

            # 현재 component 안에서 c의 자손들만 선택
            for v in order:
                if v != 1 and left_tin <= tin[v] < right_tin:
                    down = depth[v] - depth_c

                    if down < k:
                        down_nodes.append(v)
                        if down > max_down:
                            max_down = down

            if down_nodes:
                q_count = len(down_nodes)

                # 작은 경우 직접 확인
                if max_up * q_count <= 16 * (max_up + q_count):
                    for v in down_nodes:
                        limit = k - 1 - (depth[v] - depth_c)

                        if limit >= max_up:
                            limit = max_up - 1

                        if limit < 0:
                            continue

                        x = z[v]
                        best_line = NEG_INF

                        for idx in range(limit + 1):
                            u = up_nodes[idx]
                            value = intercept[u] + line_slope[u] * x

                            if value > best_line:
                                best_line = value

                        candidate = base[v] + best_line
                        if candidate > answer:
                            answer = candidate

                # 모든 up 후보가 모든 v에 대해 허용되는 경우
                elif max_down + max_up <= k:
                    hull = build_hull(up_nodes[:max_up])
                    hull_len = len(hull)

                    # x가 증가하는 순서로 처리하면 hull pointer를 이동시킬 수 있다.
                    down_nodes.sort(key=z.__getitem__)

                    hull_pos = 0

                    for v in down_nodes:
                        x = z[v]

                        while hull_pos + 1 < hull_len:
                            current_line = hull[hull_pos]
                            next_line = hull[hull_pos + 1]

                            current_value = (
                                intercept[current_line] +
                                line_slope[current_line] * x
                            )
                            next_value = (
                                intercept[next_line] +
                                line_slope[next_line] * x
                            )

                            if next_value >= current_value:
                                hull_pos += 1
                            else:
                                break

                        line_id = hull[hull_pos]
                        best_line = (
                            intercept[line_id] +
                            line_slope[line_id] * x
                        )

                        candidate = base[v] + best_line
                        if candidate > answer:
                            answer = candidate

                else:
                    # 깊은 v부터 처리하면 허용되는 up prefix가 점점 커진다.
                    down_nodes.sort(
                        key=depth.__getitem__,
                        reverse=True
                    )

                    version += 1
                    current_version = version
                    next_up = 0

                    for v in down_nodes:
                        limit = k - 1 - (depth[v] - depth_c)

                        while next_up < max_up and next_up <= limit:
                            add_line(
                                up_nodes[next_up],
                                current_version
                            )
                            next_up += 1

                        best_line = query_line(
                            compressed_x[v],
                            current_version
                        )

                        candidate = base[v] + best_line
                        if candidate > answer:
                            answer = candidate

        # centroid 제거 후 남은 컴포넌트들을 작업 목록에 추가
        removed[c] = 1

        for to in adjacency[c]:
            if not removed[to]:
                tasks.append(to)

    if answer == NEG_INF:
        answer = 0

    sys.stdout.write(str(answer) + "\n")


if __name__ == "__main__":
    solve()