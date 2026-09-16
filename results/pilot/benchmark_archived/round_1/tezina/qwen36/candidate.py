import sys

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    n = int(input_data[0])
    k = int(input_data[1])
    a = map(int, input_data[2:])
    
    cnt = [0] * 100001
    for x in a:
        cnt[x] += 1
        
    ans = 0
    CAP = 100000000
    
    for x in range(1, 100001):
        if cnt[x] == 0:
            continue
            
        limit = k if k < x else x
        w = 1
        total_x = 0
        
        while w <= limit:
            v = x // w
            r = x // v
            if r > limit:
                r = limit
                
            count = r - w + 1
            term = v * (x + 2)
            if term > CAP:
                term = CAP
                
            total_x += count * term
            w = r + 1
            
        ans += total_x * cnt[x]
        
    print(ans)

if __name__ == '__main__':
    solve()