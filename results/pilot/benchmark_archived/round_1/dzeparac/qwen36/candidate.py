import sys

def main():
    n = int(sys.stdin.readline())
    mod = 10**9 + 7
    print(pow(2, n // 2, mod))

if __name__ == '__main__':
    main()