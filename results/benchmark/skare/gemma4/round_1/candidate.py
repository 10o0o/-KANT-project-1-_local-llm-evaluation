import sys

def solve():
    # Read all input from standard input
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    # The first two numbers are n and k
    n = int(input_data[0])
    k = int(input_data[1])
    
    # Initialize the list of strips with the original strip of length n
    strips = [n]
    
    # Pointer to track our position in the input_data list
    ptr = 2
    
    # Process each of the k instructions
    for _ in range(k):
        # x is the 1-based index of the strip to be cut
        # l is the length at which the strip is cut
        x = int(input_data[ptr])
        l = int(input_data[ptr + 1])
        ptr += 2
        
        # Find the current length of the x-th strip
        # Since x is 1-based, we use index x-1
        current_length = strips[x-1]
        
        # Replace the x-th strip with two new strips: l and (current_length - l)
        # Using slice assignment to replace one element with two
        strips[x-1:x] = [l, current_length - l]
        
    # Use a set to find the number of distinct strip lengths
    distinct_lengths = len(set(strips))
    
    # Print the result to standard output
    print(distinct_lengths)

if __name__ == "__main__":
    solve()