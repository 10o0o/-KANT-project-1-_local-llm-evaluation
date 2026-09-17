import sys

def main():
    data = sys.stdin.read().split()
    if not data:
        return
    it = iter(data)
    n = int(next(it))
    m = int(next(it))
    k = int(next(it))
    friends = [int(next(it)) for _ in range(k)]
    friends_sorted = sorted(friends)
    
    grid = []
    for i in range(n):
        row = []
        for j in range(m):
            row.append(int(next(it)))
        grid.append(row)
    
    M = [[0] * m for _ in range(n)]
    for j in range(m):
        current_max = 0
        for i in range(1, n):
            if grid[i-1][j] != 0:
                if grid[i-1][j] > current_max:
                    current_max = grid[i-1][j]
            M[i][j] = current_max

    empty = [[0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            if grid[i][j] == 0:
                empty[i][j] = 1

    prefix = [[0] * (m+1) for _ in range(n)]
    for i in range(n):
        for j in range(1, m+1):
            prefix[i][j] = prefix[i][j-1] + empty[i][j-1]
            
    count = 0
    for i in range(n):
        for j in range(0, m - k + 1):
            if prefix[i][j+k] - prefix[i][j] < k:
                continue
            req = M[i][j:j+k]
            req.sort()
            valid = True
            for t in range(k):
                if friends_sorted[t] <= req[t]:
                    valid = False
                    break
            if valid:
                count += 1
                
    print(count)

if __name__ == "__main__":
    main()