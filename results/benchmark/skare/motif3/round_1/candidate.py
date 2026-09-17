def main():
    import sys
    data = sys.stdin.read().split()
    n = int(data[0])
    k = int(data[1])
    strips = [n]
    index = 2
    for _ in range(k):
        x = int(data[index])
        l_val = int(data[index + 1])
        index += 2
        current_strip = strips[x - 1]
        strips[x - 1:x] = [l_val, current_strip - l_val]
    print(len(set(strips)))

if __name__ == "__main__":
    main()