import sys

def solve():
    data = sys.stdin.read().split()
    if not data:
        return
    n, m = map(int, data[:2])
    grid = data[2:]

    def count_hvhv(n, m, grid):
        cnt1 = [row.count('1') for row in grid]
        cnt2 = [0] * m
        for r in range(n):
            for c in range(m):
                if grid[r][c] == '1':
                    cnt2[c] += 1

        S = [0] * n
        for r in range(n):
            s = 0
            for c in range(m):
                if grid[r][c] == '1':
                    s += cnt2[c] - 1
            S[r] = s

        T = [0] * m
        for c in range(m):
            t = 0
            for r in range(n):
                if grid[r][c] == '1':
                    t += S[r]
            T[c] = t

        sum_T = [0] * n
        for r in range(n):
            st = 0
            for c in range(m):
                if grid[r][c] == '1':
                    st += T[c]
            sum_T[r] = st

        part1 = 0
        for r in range(n):
            if cnt1[r] > 1:
                part1 += (cnt1[r] - 1) * (sum_T[r] - S[r] * cnt1[r])

        rows_int = [int(row, 2) for row in grid]
        part2 = 0
        for i in range(n):
            ri = rows_int[i]
            for j in range(i + 1, n):
                ic = (ri & rows_int[j]).bit_count()
                if ic:
                    part2 += ic * ic
        part2 *= 2

        V = [0] * m
        for c in range(m):
            v = 0
            for r in range(n):
                if grid[r][c] == '1':
                    v += cnt1[r] - 1
            V[c] = v

        corr1 = 0
        for c in range(m):
            if cnt2[c] > 1:
                corr1 += V[c] * (cnt2[c] - 1) ** 2

        corr2 = 0
        for c in range(m):
            if cnt2[c] > 1:
                corr2 += cnt2[c] * (cnt2[c] - 1)

        correction = corr1 - corr2

        return part1 - part2 - correction

    ans = count_hvhv(n, m, grid)
    grid_T = ["".join(grid[r][c] for r in range(n)) for c in range(m)]
    ans += count_hvhv(m, n, grid_T)
    print(ans)

if __name__ == '__main__':
    solve()