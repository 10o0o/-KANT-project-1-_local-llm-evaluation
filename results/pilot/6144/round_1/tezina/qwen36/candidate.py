import sys

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    iterator = iter(input_data)
    n = int(next(iterator))
    k = int(next(iterator))
    
    cnt = [0] * 100001
    max_val = 0
    
    for _ in range(n):
        val = int(next(iterator))
        cnt[val] += 1
        if val > max_val:
            max_val = val
            
    total_sum = 0
    LIMIT = 10**8
    
    for v in range(1, max_val + 1):
        if cnt[v] == 0:
            continue
            
        freq = cnt[v]
        limit_w = k if k < v else v
        w = 1
        
        while w <= limit_w:
            q = v // w
            if q == 0:
                break
                
            r = v // q
            if r > limit_w:
                r = limit_w
                
            count_w = r - w + 1
            val = q * (v + 2)
            if val > LIMIT:
                val = LIMIT
                
            total_sum += count_w * val * freq
            w = r + 1
            
    print(total_sum)

if __name__ == '__main__':
    solve()