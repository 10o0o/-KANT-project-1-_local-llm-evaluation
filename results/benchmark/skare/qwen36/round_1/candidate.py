import sys

def main():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    iterator = iter(input_data)
    n = int(next(iterator))
    k = int(next(iterator))
    
    strips = [n]
    
    for _ in range(k):
        x = int(next(iterator))
        l = int(next(iterator))
        
        idx = x - 1
        current_len = strips[idx]
        strips[idx:idx+1] = [l, current_len - l]
        
    print(len(set(strips)))

if __name__ == '__main__':
    main()