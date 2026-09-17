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

    total_ans = 0
    cap = 100000000

    for x in range(1, 100001):
        c = cnt[x]
        if c == 0:
            continue
            
        limit = x if x < k else k
        g_x = 0
        l = 1
        while l <= limit:
            q = x // l
            r = limit if limit < x // q else x // q
            val = q * (x + 2)
            if val > cap:
                val = cap
            g_x += (r - l + 1) * val
            l = r + 1
            
        total_ans += g_x * c

    print(total_ans)

if __name__ == '__main__':
    solve()