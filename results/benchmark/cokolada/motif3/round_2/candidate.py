import sys

def main():
    data = sys.stdin.read().splitlines()
    if not data:
        return
    n, m = map(int, data[0].split())
    grid = []
    for i in range(1, 1 + n):
        grid.append(data[i].strip())
    
    if n == 0 or m == 0:
        print(0)
        return
        
    dp = [[10**9] * (m + 1) for _ in range(n + 1)]
    is_mono = [[False] * (m + 1) for _ in range(n + 1)]
    
    prefix = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            val = 1 if grid[i - 1][j - 1] == '1' else 0
            prefix[i][j] = prefix[i - 1][j] + prefix[i][j - 1] - prefix[i - 1][j - 1] + val
            
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            total = prefix[i][j]
            if total == 0 or total == i * j:
                is_mono[i][j] = True
                
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if is_mono[i][j]:
                dp[i][j] = 0
            else:
                for k in range(1, i):
                    if is_mono[k][j] and is_mono[i - k][j]:
                        dp[i][j] = min(dp[i][j], dp[k][j] + dp[i - k][j] + 1)
                    else:
                        dp[i][j] = min(dp[i][j], dp[k][j] + dp[i - k][j] + 1)
                for l in range(1, j):
                    if is_mono[i][l] and is_mono[i][j - l]:
                        dp[i][j] = min(dp[i][j], dp[i][l] + dp[i][j - l] + 1)
                    else:
                        dp[i][j] = min(dp[i][j], dp[i][l] + dp[i][j - l] + 1)
                        
    print(dp[n][m])

if __name__ == '__main__':
    main()