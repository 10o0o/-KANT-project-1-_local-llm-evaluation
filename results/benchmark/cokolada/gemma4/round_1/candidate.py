import sys

def solve():
    # Read all input from standard input
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    # The first two elements are n and m
    n = int(input_data[0])
    m = int(input_data[1])
    
    # The remaining elements are the rows of the chocolate grid
    grid = input_data[2:]

    # Count necessary horizontal cuts
    h_cuts = 0
    for i in range(n - 1):
        # Check if there's any column j where row i and row i+1 have different colors
        for j in range(m):
            if grid[i][j] != grid[i+1][j]:
                h_cuts += 1
                break

    # Count necessary vertical cuts
    v_cuts = 0
    for j in range(m - 1):
        # Check if there's any row i where column j and column j+1 have different colors
        for i in range(n):
            if grid[i][j] != grid[i][j+1]:
                v_cuts += 1
                break

    # The total minimum number of cuts is the sum of horizontal and vertical cuts
    print(h_cuts + v_cuts)

if __name__ == "__main__":
    solve()