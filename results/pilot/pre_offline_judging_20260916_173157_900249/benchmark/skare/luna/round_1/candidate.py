import sys


def main():
    input = sys.stdin.buffer.readline

    n, k = map(int, input().split())
    pieces = [n]

    for _ in range(k):
        x, l = map(int, input().split())
        index = x - 1
        old_length = pieces[index]

        pieces[index:index + 1] = [l, old_length - l]

    print(len(set(pieces)))


if __name__ == "__main__":
    main()