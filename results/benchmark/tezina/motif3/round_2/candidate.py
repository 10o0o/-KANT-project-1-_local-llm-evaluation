import sys

def main():
    data = sys.stdin.read().split()
    if not data:
        print(0)
        return
    n = int(data[0])
    k = int(data[1])
    a = list(map(int, data[2:2+n]))
    if n == 0:
        print(0)
        return

    max_val = max(a)
    cnt = [0] * (max_val + 1)
    for x in a:
        if x <= max_val:
            cnt[x] += 1

    prefix_cnt = [0] * (max_val + 1)
    prefix_sumx = [0] * (max_val + 1)
    for i in range(1, max_val + 1):
        prefix_cnt[i] = prefix_cnt[i - 1] + cnt[i]
        prefix_sumx[i] = prefix_sumx[i - 1] + i * cnt[i]

    T = 10**8
    ans_w = [0] * (k + 2)

    for q in range(1, max_val + 1):
        w_max = min(k, max_val // q)
        if w_max < 1:
            continue
        X0 = T // q - 2

        for w in range(1, w_max + 1):
            L = q * w
            if L > max_val:
                continue
            R = q * w + w - 1
            if R > max_val:
                R = max_val

            total_val = 0

            L1 = L
            R1 = min(R, X0)
            if R1 >= L1:
                cnt1 = prefix_cnt[R1] - prefix_cnt[L1 - 1]
                sumx1 = prefix_sumx[R1] - prefix_sumx[L1 - 1]
                total1 = q * (sumx1 + 2 * cnt1)
                total_val += total1

            L2 = max(L, X0 + 1)
            R2 = R
            if R2 >= L2:
                cnt2 = prefix_cnt[R2] - prefix_cnt[L2 - 1]
                total2 = T * cnt2
                total_val += total2

            ans_w[w] += total_val

    result = sum(ans_w[1:k + 1])
    print(result)

if __name__ == '__main__':
    main()