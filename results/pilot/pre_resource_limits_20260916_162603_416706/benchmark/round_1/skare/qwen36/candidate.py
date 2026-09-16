import sys

def main():
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    n = int(input_data[0])
    k = int(input_data[1])
    
    strips = [n]
    idx = 2
    for _ in range(k):
        x = int(input_data[idx])
        l = int(input_data[idx + 1])
        idx += 2
        
        current_len = strips[x - 1]
        strips[x - 1 : x + 1] = [l, current_len - l]
        
    print(len(set(strips)))

if __name__ == '__main__':
    main()