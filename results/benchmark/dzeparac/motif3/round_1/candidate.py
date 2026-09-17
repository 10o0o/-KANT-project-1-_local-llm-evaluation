MOD = 10**9 + 7

def main():
    n = int(input().strip())
    M = n // 2
    result = pow(2, M, MOD)
    print(result)

if __name__ == '__main__':
    main()