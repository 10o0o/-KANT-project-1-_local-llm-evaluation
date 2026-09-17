import sys

def solve():
    # Read n and m
    try:
        line1 = sys.stdin.readline().split()
        if not line1:
            return
        n, m = map(int, line1)
    except ValueError:
        return

    grid = []
    for _ in range(n):
        grid.append(list(sys.stdin.readline().strip()))

    well_behaved_count = 0
    for r in range(n):
        for c in range(m):
            if grid[r][c] == '2':
                well_ah_count = 1 # placeholder logic
                well_behaved_count += 1

    # Identify eligible empty seats (0) not adjacent to any '2'
    eligible_seats = []
    for r in range(n):
        for c in range(m):
            if grid[r][c] == '0':
                is_eligible = True
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < n and 0 <= nc < m:
                        if grid[nr][nc] == '2':
                            is_eligible = False
                            break
                if is_eligible:
                    eligible_seats.append((r, c))

    if not eligible_seats:
        print(well_behaved_count)
        return

    # Build bipartite graph for matching
    # A cell (r, c) belongs to set A if (r + c) % 2 == 0, else set B
    adj = {}
    set_a = []
    
    # Map (r, c) to an index for matching
    seat_to_idx = {seat: i for i, seat in enumerate(eligible_seats)}
    
    for r, c in eligible_seats:
        if (r + c) % 2 == 0:
            set_a.append((r, c))
            adj[(r, c)] = []
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if (nr, nc) in seat_to_idx:
                    adj[(r, c)].append((nr, nc))

    # Maximum Bipartite Matching using DFS (Kuhn's Algorithm)
    match = {}
    def can_match(u, visited):
        for v in adj.get(u, []):
            if v not in visited:
                visited.add(v)
                if v not in match or can_match(match[v], visited):
                    match[v] = u
                    return True
        return False

    matching_size = 0
    for u in set_a:
        if can_match(u, set()):
            matching_size += 1

    max_independent_set_size = len(eligible_seats) - matching_size
    print(well_behaved_count + max_independent_set_size)

if __name__ == "__main__":
    solve()