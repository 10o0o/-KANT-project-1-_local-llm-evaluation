def main():
    import sys
    n, k = map(int, sys.stdin.readline().split())
    strips = [n]
    
    for _ in range(k):
        x, l_val = map(int, sys.stdin.readline().split())
        idx = x - 1
        current_len = strips.pop(idx)
        strips.insert(idx, l_val)
        strips.insert(idx + 1, current_len - l_val)
    
    distinct_count = len(set(strips))
    print(distinct_count)

if __name__ == '__main__':
    main()