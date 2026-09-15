import sys


def main():
    input = sys.stdin.readline

    n, k = map(int, input().split())
    strips = [n]

    for _ in range(k):
        x, l = map(int, input().split())

        index = x - 1
        current_length = strips[index]

        strips[index : index + 1] = [
            l,
            current_length - l,
        ]

    print(len(set(strips)))


if __name__ == "__main__":
    main()
