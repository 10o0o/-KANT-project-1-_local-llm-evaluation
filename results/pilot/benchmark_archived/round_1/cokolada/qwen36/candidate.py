import sys

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    n = int(input_data[0])
    m = int(input_data[1])
    grid = input_data[2:]
    
    cuts = 0
    
    # 인접한 행이 다른 경우 수평 컷 추가
    for i in range(n - 1):
        if grid[i] != grid[i+1]:
            cuts += 1
            
    # 인접한 열이 다른 경우 수직 컷 추가
    for j in range(m - 1):
        for i in range(n):
            if grid[i][j] != grid[i][j+1]:
                cuts += 1
                break
                
    print(cuts)

if __name__ == '__main__':
    solve()