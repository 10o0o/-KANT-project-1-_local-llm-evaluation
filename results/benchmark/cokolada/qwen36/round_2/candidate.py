import sys

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    n = int(input_data[0])
    m = int(input_data[1])
    grid = input_data[2:]
    
    cuts = 0
    
    # 수평 컷 확인: 인접한 행 사이에 색이 다른 열이 하나라도 있으면 컷 필요
    for i in range(n - 1):
        for j in range(m):
            if grid[i][j] != grid[i+1][j]:
                cuts += 1
                break
                
    # 수직 컷 확인: 인접한 열 사이에 색이 다른 행이 하나라도 있으면 컷 필요
    for j in range(m - 1):
        for i in range(n):
            if grid[i][j] != grid[i][j+1]:
                cuts += 1
                break
                
    print(cuts)

if __name__ == '__main__':
    solve()