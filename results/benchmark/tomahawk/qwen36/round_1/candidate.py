import sys
import bisect

def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    iterator = iter(input_data)
    n = int(next(iterator))
    q = int(next(iterator))

    D = []
    R = []
    L = []

    for _ in range(q):
        s = next(iterator)
        x = int(next(iterator))
        if s == 'D':
            D.append(x)
        elif s == 'R':
            R.append(x)
        elif s == 'L':
            L.append(x)

    # A(r) 분석: 단조 증가 함수
    # A(1) = sum(max(0, x - n + 1))
    # A(n) = sum(x)
    sum_D = sum(D)
    min_A = sum(max(0, x - n + 1) for x in D)
    max_A = sum_D
    delta_A = max_A - min_A

    # B(c) 평가를 위한 전처리
    R.sort()
    L.sort()

    R_prefix = [0] * (len(R) + 1)
    for i, val in enumerate(R):
        R_prefix[i+1] = R_prefix[i] + val
    total_sum_R = R_prefix[-1]

    L_prefix = [0] * (len(L) + 1)
    for i, val in enumerate(L):
        L_prefix[i+1] = L_prefix[i] + val
    total_sum_L = L_prefix[-1]

    def eval_B(c):
        # R 연산 기여도: x >= n - c + 1 인 것만 기여
        val_R = n - c + 1
        idx_R = bisect.bisect_left(R, val_R)
        cnt_R = len(R) - idx_R
        sum_R = total_sum_R - R_prefix[idx_R]
        res = cnt_R * (c - n) + sum_R

        # L 연산 기여도: x >= c 인 것만 기여
        idx_L = bisect.bisect_left(L, c)
        cnt_L = len(L) - idx_L
        sum_L = total_sum_L - L_prefix[idx_L]
        res += sum_L - cnt_L * (c - 1)
        return res

    # B(c)의 최대값은 경계에서 발생
    max_B = max(eval_B(1), eval_B(n))

    # B(c)는 볼록 함수이므로 삼분 탐색으로 최소값 탐색
    low, high = 1, n
    while high - low > 2:
        m1 = low + (high - low) // 3
        m2 = high - (high - low) // 3
        if eval_B(m1) < eval_B(m2):
            high = m2
        else:
            low = m1

    min_B = min(eval_B(c) for c in range(low, high + 1))
    delta_B = max_B - min_B

    print(delta_A + delta_B)

if __name__ == '__main__':
    solve()