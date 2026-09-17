import sys
sys.setrecursionlimit(10000)

def main():
    data = sys.stdin.read().splitlines()
    if not data:
        return
    n, m = map(int, data[0].split())
    grid = []
    for i in range(1, 1+n):
        grid.append(data[i].strip())
    
    fixed_count = 0
    for i in range(n):
        for j in range(m):
            if grid[i][j] == '2':
                fixed_count += 1
                
    available = [[False] * m for _ in range(n)]
    directions = [(0,1), (0,-1), (1,0), (-1,0)]
    
    for i in range(n):
        for j in range(m):
            if grid[i][j] != '0':
                continue
            has_bad_neighbor = False
            for dx, dy in directions:
                ni, nj = i + dx, j + dy
                if 0 <= ni < n and 0 <= nj < m:
                    if grid[ni][nj] == '2':
                        has_bad_neighbor = True
                        break
            available[i][j] = not has_bad_neighbor

    left_nodes = []
    right_nodes = []
    for i in range(n):
        for j in range(m):
            if available[i][j]:
                if (i + j) % 2 == 0:
                    left_nodes.append((i, j))
                else:
                    right_nodes.append((i, j))
                   
    total_available = len(left_nodes) + len(right_nodes)
    
    if total_available == 0:
        print(fixed_count)
        return
        
    right_index = {}
    for idx, pos in enumerate(right_nodes):
        right_index[pos] = idx
        
    graph = [[] for _ in range(len(left_nodes))]
    for u, (i, j) in enumerate(left_nodes):
        for dx, dy in directions:
            ni, nj = i + dx, j + dy
            if 0 <= ni < n and 0 <= nj < m and available[ni][nj]:
                pos = (ni, nj)
                if pos in right_index:
                    v = right_index[pos]
                    graph[u].append(v)
                   
    match = [-1] * len(right_nodes)
    
    def dfs(u, visited):
        for v in graph[u]:
            if not visited[v]:
                visited[v] = True
                if match[v] == -1 or dfs(match[v], visited):
                    match[v] = u
                    return True
        return False
                   
    matching_count = 0
    for u in range(len(left_nodes)):
        visited = [False] * len(right_nodes)
        if dfs(u, visited):
            matching_count += 1
            
    independent_set = total_available - matching_count
    total_students = fixed_count + independent_set
    print(total_students)

if __name__ == "__main__":
    main()