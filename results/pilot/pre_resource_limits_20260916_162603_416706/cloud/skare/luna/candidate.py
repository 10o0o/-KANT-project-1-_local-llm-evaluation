import sys

def main():
    input = sys.stdin.buffer.readline

    n, k = map(int, input().split())
    strips = [n]

    for _ in range(k):
        x, l = map(int, input().split())

        original_length = strips[x - 1]
        strips[x - 1:x] = [l, original_length - l]

    print(len(set(strips)))


if __name__ == "__main__":
    main()