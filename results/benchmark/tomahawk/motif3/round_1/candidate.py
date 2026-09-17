import sys
import bisect

def main():
    data = sys.stdin.read().splitlines()
    if not data:
        print(0)
        return
    n, q = map(int, data[0].split())
    D_ops = []
    R_ops = []
    L_ops = []
    for i in range(1, 1 + q):
        parts = data[i].split()
        if not parts:
            continue
        s = parts[0]
        x = int(parts[1])
        if s == 'D':
            D_ops.append(x)
        elif s == 'R':
            R_ops.append(x)
        elif s == 'L':
            L_ops.append(x)
    
    sumD = sum(D_ops)
    count_n = sum(1 for x in D_ops if x == n)
    diff_f = sumD - count_n

    events = set()
    events.add(0)
    events.add(n - 1)
    for x in L_ops:
        if 0 <= x <= n - 1:
            events.add(x)
    for x in R_ops:
        cand = n - 1 - x
        if 0 <= cand <= n - 1:
            events.add(cand)
    events = sorted(events)
    
    A = [n - 1 - x for x in R_ops]
    A_sorted = sorted(A)
    prefixA = [0] * (len(A_sorted) + 1)
    for i in range(1, len(A_sorted) + 1):
        prefixA[i] = prefixA[i - 1] + A_sorted[i - 1]
    
    B_sorted = sorted(L_ops)
    suffixB = [0] * (len(B_sorted) + 1)
    for i in range(len(B_sorted) - 1, -1, -1):
        suffixB[i] = suffixB[i + 1] + B_sorted[i]
    
    min_g = float('inf')
    max_g = float('-inf')
    
    for j in events:
        idxA = bisect.bisect_left(A_sorted, j)
        countA = idxA
        sumA = prefixA[idxA]
        hR = j * countA - sumA
        
        idxB = bisect.bisect_right(B_sorted, j)
        countB = len(B_sorted) - idxB
        sumB = suffixB[idxB]
        hL = sumB - j * countB
        
        g_val = hR + hL
        if g_val < min_g:
            min_g = g_val
        if g_val > max_g:
            max_g = g_val
    
    diff_g = max_g - min_g
    ans = diff_f + diff_g
    print(ans)

if __name__ == "__main__":
    main()