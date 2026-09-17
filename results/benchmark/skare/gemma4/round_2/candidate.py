import sys

def solve():
    # Read all input from standard input
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    # The first two numbers are n and k
    n = int(input_data[0])
    k = int(input_data[1])
    
    # Initialize the list of strips with the original length n
    strips = [n]
    
    # Pointer to traverse the input data
    idx = 2
    for _ in range(k):
        # x is the index of the strip to cut (1-based)
        # l is the position at which to cut the strip
        x = int(input_data[idx])
        l = int(input_data[idx+1])
        idx += 2
        
        # The x-th strip is at index x-1 in our 0-indexed list
        target_index = x - 1
        original_length = strips[target_index]
        
        # Replace the original strip with the two new pieces
        # The first piece has length l
        # The second piece has length original_length - l
        strips[target_index] = l
        strips.insert(x, original_length - l)
        
    # Use a set to find the number of distinct strip lengths
    distinct_lengths = set(strips)
    print(len(distinct_lengths))

if __name__ == "__main__":
    solve()