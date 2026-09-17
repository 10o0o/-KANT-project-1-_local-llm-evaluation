import sys

def main():
    input = sys.stdin.buffer.readline

    n, m = map(int, input().split())
    grid = [input().strip() for _ in range(n)]

    answer = 0

    # 인접한 두 행 사이의 경계 확인
    for i in range(n - 1):
        if any(grid[i][j] != grid[i + 1][j] for j in range(m)):
            answer += 1

    # 인접한 두 열 사이의 경계 확인
    for j in range(m - 1):
        if any(grid[i][j] != grid[i][j + 1] for i in range(n)):
            answer += 1

    print(answer)

if __name__ == "__main__":
    main()