import sys


def main():
    input = sys.stdin.buffer.readline

    n, m = map(int, input().split())

    previous_row = None
    horizontal_cuts = 0
    vertical_needed = [False] * (m - 1)

    for _ in range(n):
        row = input().strip()

        if previous_row is not None and row != previous_row:
            horizontal_cuts += 1

        for col in range(m - 1):
            if row[col] != row[col + 1]:
                vertical_needed[col] = True

        previous_row = row

    print(horizontal_cuts + sum(vertical_needed))


if __name__ == "__main__":
    main()