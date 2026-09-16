import sys


def solve():
    data = sys.stdin.buffer.read().split()
    if not data:
        return

    n, m = map(int, data[:2])
    grid = data[2:2 + n]

    cuts = 0

    # 인접한 행이 다르면 가로 절단이 필요하다.
    for i in range(1, n):
        if grid[i] != grid[i - 1]:
            cuts += 1

    # 인접한 열이 다르면 세로 절단이 필요하다.
    for j in range(1, m):
        for i in range(n):
            if grid[i][j] != grid[i][j - 1]:
                cuts += 1
                break

    print(cuts)


if __name__ == "__main__":
    solve()