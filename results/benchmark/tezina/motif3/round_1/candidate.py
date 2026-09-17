import sys

def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    k = int(data[1])
    a = list(map(int, data[2:2+n]))
    
    if n == 0:
        print(0)
        return
        
    max_val = max(a)
    freq = [0] * (max_val + 1)
    for num in a:
        if num <= max_val:
            freq[num] += 1
            
    F = [0] * (max_val + 1)
    G = [0] * (max_val + 1)
    for i in range(1, max_val + 1):
        F[i] = F[i - 1] + freq[i]
        G[i] = G[i - 1] + i * freq[i]
    
    def get_freq_sum(L, R):
        if L > R:
            return 0
        L = max(1, L)
        R = min(max_val, R)
        if L > R:
            return 0
        return F[R] - F[L - 1]
    
    def get_x_freq_sum(L, R):
        if L > R:
            return 0
        L = max(1, L)
        R = min(max_val, R)
        if L > R:
            return 0
        return G[R] - G[L - 1]
    
    M = 100000000
    total_ans = 0
    w_max = min(k, max_val)
    
    for w in range(1, w_max + 1):
        q_max = max_val // w
        for q in range(1, q_max + 1):
            L_bound = q * w
            if L_bound > max_val:
                break
            R_bound = min((q + 1) * w - 1, max_val)
            if 2 * q >= M:
                cnt = get_freq_sum(L_bound, R_bound)
                total_ans += M * cnt
            else:
                num = M - 2 * q
                x0 = (num + q - 1) // q
                R1 = min(R_bound, x0 - 1)
                if L_bound <= R1:
                    s1 = get_x_freq_sum(L_bound, R1)
                    s2 = get_freq_sum(L_bound, R1)
                    total_ans += q * s1 + 2 * q * s2
                L2 = max(L_bound, x0)
                if L2 <= R_bound:
                    cnt = get_freq_sum(L2, R_bound)
                    total_ans += M * cnt
                   
    print(total_ans)

if __name__ == "__main__":
    main()