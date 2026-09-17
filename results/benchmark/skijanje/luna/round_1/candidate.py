import sys
from array import array

MAX_X = 100000
TREE_SIZE = 4 * MAX_X + 5
SHIFT = 20
MASK = (1 << SHIFT) - 1
NEG = -10**30

LINE_SLOPE = []
LINE_INTERCEPT = []


class HullStack:
    __slots__ = ("tree", "changes", "marks", "items")

    def __init__(self):
        self.tree = [-1] * TREE_SIZE
        self.changes = array("Q")
        self.marks = []
        self.items = []

    def push(self, line):
        changes = self.changes
        self.marks.append(len(changes))
        self.items.append(line)

        tree = self.tree
        slopes = LINE_SLOPE
        intercepts = LINE_INTERCEPT

        new_line = line
        new_m = slopes[new_line]
        new_c = intercepts[new_line]

        lo = 1
        hi = MAX_X
        node = 1

        while True:
            old_line = tree[node]

            if old_line == -1:
                changes.append(node << SHIFT)
                tree[node] = new_line
                break

            mid = (lo + hi) >> 1
            old_m = slopes[old_line]
            old_c = intercepts[old_line]

            if new_m * mid + new_c > old_m * mid + old_c:
                changes.append((node << SHIFT) | (old_line + 1))
                tree[node] = new_line

                new_line = old_line
                new_m = old_m
                new_c = old_c

            if lo == hi:
                break

            current_line = tree[node]
            current_m = slopes[current_line]
            current_c = intercepts[current_line]

            if new_m * lo + new_c > current_m * lo + current_c:
                node <<= 1
                hi = mid
            elif new_m * hi + new_c > current_m * hi + current_c:
                node = (node << 1) | 1
                lo = mid + 1
            else:
                break

    def pop(self):
        line = self.items.pop()
        mark = self.marks.pop()

        changes = self.changes
        tree = self.tree

        i = len(changes) - 1
        while i >= mark:
            code = changes[i]
            tree[code >> SHIFT] = (code & MASK) - 1
            i -= 1

        del changes[mark:]
        return line

    def clear(self):
        while self.items:
            self.pop()

    def query(self, x):
        if not self.items:
            return NEG

        tree = self.tree
        slopes = LINE_SLOPE
        intercepts = LINE_INTERCEPT

        lo = 1
        hi = MAX_X
        node = 1
        best = NEG

        while True:
            line = tree[node]
            if line != -1:
                value = slopes[line] * x + intercepts[line]
                if value > best:
                    best = value

            if lo == hi:
                break

            mid = (lo + hi) >> 1
            if x <= mid:
                node <<= 1
                hi = mid
            else:
                node = (node << 1) | 1
                lo = mid + 1

        return best


class LineDeque:
    __slots__ = ("left", "right")

    def __init__(self):
        self.left = HullStack()
        self.right = HullStack()

    def push_left(self, line):
        self.left.push(line)

    def push_right(self, line):
        self.right.push(line)

    def _rebalance_left(self):
        left = self.left
        right = self.right

        sequence = right.items[:]
        right.clear()

        half = (len(sequence) + 1) // 2

        for i in range(half - 1, -1, -1):
            left.push(sequence[i])
        for i in range(half, len(sequence)):
            right.push(sequence[i])

    def _rebalance_right(self):
        left = self.left
        right = self.right

        sequence = left.items[::-1]
        left.clear()

        half = len(sequence) // 2

        for i in range(half - 1, -1, -1):
            left.push(sequence[i])
        for i in range(half, len(sequence)):
            right.push(sequence[i])

    def pop_left(self):
        if not self.left.items:
            self._rebalance_left()
        return self.left.pop()

    def pop_right(self):
        if not self.right.items:
            self._rebalance_right()
        return self.right.pop()

    def query(self, x):
        best = NEG

        if self.left.items:
            best = self.left.query(x)

        if self.right.items:
            value = self.right.query(x)
            if value > best:
                best = value

        return best


def main():
    global LINE_SLOPE, LINE_INTERCEPT

    data = list(map(int, sys.stdin.buffer.read().split()))
    if not data:
        return

    n = data[0]
    k = data[1]

    if n == 1:
        print(0)
        return

    parent_start = 2
    z_start = parent_start + (n - 1)
    b_start = z_start + (n - 1)

    if k == 1:
        answer = NEG
        for i in range(n - 1):
            z = data[z_start + i]
            b = data[b_start + i]
            value = z * (z + b) + z * z
            if value > answer:
                answer = value
        print(answer)
        return

    parent = [-1] * n
    children = [[] for _ in range(n)]

    for v in range(1, n):
        p = data[parent_start + v - 1] - 1
        parent[v] = p
        children[p].append(v)

    z = [0] + data[z_start:b_start]
    b = [0] + data[b_start:b_start + n - 1]

    prefix = [0] * n
    for v in range(1, n):
        prefix[v] = prefix[parent[v]] + b[v]

    slopes = [0] * n
    intercepts = [0] * n
    base = [0] * n

    for v in range(1, n):
        p = parent[v]
        zv = z[v]

        slopes[v] = -prefix[p]
        intercepts[v] = zv * zv
        base[v] = zv * (zv + prefix[v])

    LINE_SLOPE = slopes
    LINE_INTERCEPT = intercepts

    del data
    del parent
    del prefix
    del b

    line_deque = LineDeque()
    removed = [-1] * n

    events = children[0][::-1]
    active_count = 0
    answer = NEG

    while events:
        event = events.pop()

        if event > 0:
            v = event

            line_deque.push_right(v)

            if active_count == k:
                removed[v] = line_deque.pop_left()
            else:
                active_count += 1

            best_line = line_deque.query(z[v])
            candidate = base[v] + best_line
            if candidate > answer:
                answer = candidate

            events.append(-v)
            for child in reversed(children[v]):
                events.append(child)

        else:
            v = -event

            line_deque.pop_right()
            active_count -= 1

            old_line = removed[v]
            if old_line != -1:
                line_deque.push_left(old_line)
                active_count += 1

    print(answer)


if __name__ == "__main__":
    main()