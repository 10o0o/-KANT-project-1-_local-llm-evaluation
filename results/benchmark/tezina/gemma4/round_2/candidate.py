import sys

def solve():
    # Read n and k
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    n = int(input_data[0])
    k = int(input_data[1])
    a = list(map(int, input_data[2:]))
    
    max_a = 100000
    count = [0] * (max_a + 1)
    for x in a:
        count[x] += 1
        
    # P1[i] = sum(count[j] for j in 1..i)
    # P2[i] = sum(count[j] * j for j in 1..i)
    P1 = [0] * (max_a + 1)
    P2 = [0] * (max_a + 1)
    
    curr_p1 = 0
    curr_p2 = 0
    for i in range(1, max_a + 1):
        curr_p1 += count[i]
        curr_p2 += count[i] * i
        P1[i] = curr_p1
        P2[i] = curr_p2
        
    total_strength_sum = 0
    
    # Iterate through each weight type w from 1 to k
    # We only care about w up to max_a because for w > max_a, floor(a_i/w) = 0
    for w in range(1, min(k, max_a) + 1):
        # For a fixed w, we iterate through m = floor(a_i / w)
        # m starts from 1 because m=0 contributes 0
        for m in range(1, max_a // w + 1):
            L = m * w
            R = min((m + 1) * w - 1, max_a)
            
            if L > R:
                continue
            
            # The condition is m * (x + 2) <= 10^8
            # x <= 10^8 / m - 2
            limit = 10**8 // m - 2
            
            # Case 1: x in [L, min(R, limit)]
            R_eff = min(R, limit)
            if L <= R_eff:
                # Contribution: m * sum(count[x] * (x + 2))
                # = m * (sum(count[x]*x) + 2 * sum(count[x]))
                term_p2 = P2[R_eff] - P2[L-1]
                term_p1 = P1[R_eff] - P1[L-1]
                total_strength_sum += m * (term_p2 + 2 * term_p1)
            
            # Case 2: x in [max(L, limit + 1), R]
            L_eff = max(L, limit + 1)
            if L_eff <= R:
                # Contribution: 10^8 * sum(count[x])
                term_p1 = P1[R] - P1[L_eff-1]
                total_strength_sum += 10**8 * term_p1
                
    print(total_strength_sum)

if __name__ == "__main__":
    solve()