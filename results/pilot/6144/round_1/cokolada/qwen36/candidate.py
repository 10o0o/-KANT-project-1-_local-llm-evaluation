import sys

def solve():
    input = sys.stdin.read
    data = input().split()
    
    n = int(data[0])
    m = int(data[1])
    
    grid = data[2:]
    
    cuts = 0
    
    # 가로 자르기 확인 (인접한 행 비교)
    for i in range(n - 1):
        if grid[i] != grid[i+1]:
            cuts += 1
            
    # 세로 자르기 확인 (인접한 열 비교)
    for j in range(m - 1):
        col_diff = False
        for i in range(n):
            if grid[i][j] != grid[i][j+1]:
                col_diff = True
                break
        if col_diff:
            cuts += 1
            
    print(cuts)

if __name__ == "__main__":
    solve()