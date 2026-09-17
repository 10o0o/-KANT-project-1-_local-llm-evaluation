mod = 10**9 + 7

def main():
    n = int(input().strip())
    m = n // 2
    result = pow(2, m, mod)
    print(result)

if __name__ == '__main__':
    main()