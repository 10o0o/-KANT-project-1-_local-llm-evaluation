import sys

def solve():
    # Read n and m from the first line of input
    line = sys.stdin.readline()
    if not line:
        return
    try:
        n, m = map(int, line.split())
    except ValueError:
        return

    # Read the grid
    grid = []
    for _ in range(n):
        row = sys.stdin.readline().strip()
        if row:
            grid.append(row)

    if not grid:
        return

    h_cuts = 0
    # Check for necessary horizontal cuts
    for i in range(n - 1):
        for j in range(m):
            if grid[i][j] != grid[i+1][j]:
                h_cuts += 1
                break

    v_cuts = 0
    # Check for necessary vertical cuts
    for j in range(m - 1):
        for i in range(n):
            if grid[i][j] != grid[i][j+1]:
                v_cuts += 1
                break

    # The minimum number of cuts is the sum of necessary horizontal and vertical cuts
    print(h_cuts + v_cuts)

if __name__ == "__main__":
    solve()