import sys
sys.setrecursionlimit(10000)

def main():
    data = sys.stdin.read().splitlines()
    if not data:
        print(0)
        return
    n, m = map(int, data[0].split())
    grid = []
    for i in range(1, 1 + n):
        grid.append(data[i].strip())
    
    count2 = 0
    for i in range(n):
        for j in range(m):
            if grid[i][j] == '2':
                count2 += 1
                
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    avail = [[False] * m for _ in range(n)]
    
    for i in range(n):
        for j in range(m):
            if grid[i][j] != '0':
                avail[i][j] = False
            else:
                has2 = False
                for dx, dy in directions:
                    ni, nj = i + dx, j + dy
                    if 0 <= ni < n and 0 <= nj < m:
                        if grid[ni][nj] == '2':
                            has2 = True
                            break
                avail[i][j] = not has2
                
    left_list = []
    right_list = []
    left_index = {}
    right_index = {}
    
    for i in range(n):
        for j in range(m):
            if avail[i][j]:
                if (i + j) % 2 == 0:
                    left_index[(i, j)] = len(left_list)
                    left_list.append((i, j))
                else:
                    right_index[(i, j)] = len(right_list)
                    right_list.append((i, j))
                   
    L = len(left_list)
    R = len(right_list)
    
    graph = [[] for _ in range(L)]
    for u, (i, j) in enumerate(left_list):
        for dx, dy in directions:
            ni, nj = i + dx, j + dy
            if 0 <= ni < n and 0 <= nj < m:
                if avail[ni][nj] and (ni, nj) in right_index:
                    v = right_index[(ni, nj)]
                    graph[u].append(v)
                   
    matchR = [-1] * R
    
    def dfs(u, visited, matchR, graph):
        for v in graph[u]:
            if not visited[v]:
                visited[v] = True
                if matchR[v] == -1 or dfs(matchR[v], visited, matchR, graph):
                    matchR[v] = u
                    return True
        return False
                   
    matching_size = 0
    for u in range(L):
        visited = [False] * R
        if dfs(u, visited, matchR, graph):
            matching_size += 1
            
    independent_set_size = L + R - matching_size
    total_students = count2 + independent_set_size
    print(total_students)

if __name__ == "__main__":
    main()