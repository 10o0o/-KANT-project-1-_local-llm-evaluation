import sys
import bisect

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    
    it = iter(data)
    n = int(next(it)); m = int(next(it)); k = int(next(it))
    heights = [int(next(it)) for _ in range(k)]
    H_sorted = sorted(heights)
    grid = []
    for i in range(n):
        row = []
        for j in range(m):
            row.append(int(next(it)))
        grid.append(row)
    
    obstacle = [[0] * m for _ in range(n)]
    for j in range(m):
        current_max = 0
        for i in range(n):
            obstacle[i][j] = current_max
            if grid[i][j] > 0:
                if grid[i][j] > current_max:
                    current_max = grid[i][j]
    
    total_valid = 0
    for i in range(n):
        valid_row = [1 if grid[i][j] == 0 else 0 for j in range(m)]
        prefix_empty = [0] * (m + 1)
        for j in range(m):
            prefix_empty[j + 1] = prefix_empty[j] + valid_row[j]
            
        A = obstacle[i]
        if m - k + 1 <= 0:
            continue
            
        window = sorted(A[:k])
        j_start = 0
        if prefix_empty[k] - prefix_empty[0] == k:
            t = 0
            while t < k and window[t] < H_sorted[t]:
                t += 1
            if t == k:
                total_valid += 1
                
        for j in range(1, m - k + 1):
            if prefix_empty[j + k] - prefix_empty[j] < k:
                window.pop(bisect.bisect_left(window, A[j - 1]))
                bisect.insort(window, A[j + k - 1])
                continue
                
            window.pop(bisect.bisect_left(window, A[j - 1]))
            bisect.insort(window, A[j + k - 1])
            t = 0
            while t < k and window[t] < H_sorted[t]:
                t += 1
            if t == k:
                total_valid += 1
                
    print(total_valid)

if __name__ == "__main__":
    main()