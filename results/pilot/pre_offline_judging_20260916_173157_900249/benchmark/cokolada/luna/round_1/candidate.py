import sys


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return

    n = int(data[0])
    m = int(data[1])
    grid = data[2:2 + n]

    cuts = 0

    # 서로 다른 인접 행 사이의 수평 절단
    for i in range(n - 1):
        if grid[i] != grid[i + 1]:
            cuts += 1

    # 서로 다른 인접 열 사이의 수직 절단
    for j in range(m - 1):
        for i in range(n):
            if grid[i][j] != grid[i][j + 1]:
                cuts += 1
                break

    print(cuts)


if __name__ == "__main__":
    main()