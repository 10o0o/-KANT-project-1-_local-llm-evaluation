import sys

def main():
    # Read all input from stdin
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    # n: initial length, k: number of instructions
    n = int(input_data[0])
    k = int(input_data[1])
    
    # strips stores the current lengths of all pieces
    strips = [n]
    
    # Pointer to traverse the input_data list
    ptr = 2
    for _ in range(k):
        # x: the index of the strip to cut (1-indexed)
        # l: the position at which to cut the strip
        x = int(input_data[ptr])
        l = int(input_data[ptr+1])
        ptr += 2
        
        # Convert 1-based index to 0-based index
        target_idx = x - 1
        
        # Get the current length of the strip to be cut
        current_length = strips[target_idx]
        
        # Replace the strip at target_idx with two new strips: l and (current_length - l)
        # Using slice assignment to handle the replacement and expansion
        strips[target_idx:target_idx+1] = [l, current_length - l]
        
    # The result is the number of unique lengths in the strips list
    print(len(set(strips)))

if __name__ == "__main__":
    main()