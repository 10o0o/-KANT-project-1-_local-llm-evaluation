import sys

def main():
    n = int(sys.stdin.read().strip())
    print(pow(2, n // 2, 10**9 + 7))

if __name__ == '__main__':
    main()