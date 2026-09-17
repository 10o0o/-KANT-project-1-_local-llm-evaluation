def main():
    import sys
    data = sys.stdin.read().splitlines()
    n, m = map(int, data[0].split())
    grid = []
    for i in range(1, 1+n):
        grid.append(data[i].strip())
    
    h_cuts = 0
    for i in range(n-1):
        for j in range(m):
            if grid[i][j] != grid[i+1][j]:
                h_cuts += 1
                break
                
    v_cuts = 0
    for j in range(m-1):
        for i in range(n):
            if grid[i][j] != grid[i][j+1]:
                v_cuts += 1
                break
                
    print(h_cuts + v_cuts)

if __name__ == "__main__":
    main()