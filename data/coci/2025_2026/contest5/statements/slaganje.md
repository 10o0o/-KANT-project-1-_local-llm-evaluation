# Task Slaganje

Croatian Open Competition in Informatics — Round 5, February 21th 2026

- Time limit: 1 second
- Memory limit: 512 MiB
- Score: 110 points
- Source: [contest5_tasks.pdf](../contest5_tasks.pdf#page=7), PDF pages 7–8 (cover included).

Mr. Malnar has ordered a tree with $N$ vertices labeled with integers $1,2,...,N$. Unfortunately, there was a misunderstanding between Mr. Malnar and the sender so Mr. Malnar recieved $N$ copies of the ordered tree.

While waiting for an answer from the sender, Mr. Malnar started placing trees around a regular polygon with $N$ vertices also labeled with integers $1,2,...,N$. More precisely, he placed every vertex of every tree on some vertex of the polygon such that no two vertices belonging to the same tree were placed on the same vertex of the polygon.

Mr. Malnar quickly realized that all diagonals and all sides have been covered by edges. To make sure it was not a coincidence, he tried achieving the same result again from scratch. This turned out to be too difficult for him so Mr. Malnar asks for your help!

Formally, Mr. Malnar is looking for integers $(p_{ij})$ $1 \le i,j \le N$ such that for every $i=1,...,N$ the array $a_j := p_{ij}, 1 \le j \le N$ is a permutation of integers $1,2,...,N$ and that for every $1 \le i < j \le N$ there exists an integer $k$ such that the edge between vertices $p_{ki}$ and $p_{kj}$ is a part of the ordered tree.

It can be proven that such a collection of integers exists for every tree.

## Input

The first line contains an integer $N$ ($3 \le N \le 2000$), the number of vertices in the tree/polygon.

Each of the following $N-1$ lines contains two integers $u$ and $v$ ($1 \le u,v \le N$), labels of vertices connected by an edge in the tree.

## Output

Output integers $(p_{ij})$ in $N$ rows.

In the $i$-th row output integers $p_{i1},p_{i2},...,p_{iN}$ in that order.

## Scoring

| Subtask | Points | Constraints |
| --- | --- | --- |
| 1 | 10 | There exists a vertex $u$ that is a part of every edge. |
| 2 | 15 | $N \le 10$ |
| 3 | 20 | The tree is a path graph. |
| 4 | 25 | $N \le 300$ |
| 5 | 40 | No additional constraints. |

## Examples

### Example 1

Input

```text
3
1 2
1 3
```

Output

```text
2 3 1
1 2 3
3 1 2
```

### Example 2

Input

```text
4
1 2
1 3
2 4
```

Output

```text
1 4 3 2
3 2 1 4
2 1 4 3
4 3 2 1
```

### Example 3

Input

```text
8
1 2
1 3
2 4
2 5
3 6
4 7
5 8
```

Output

```text
8 1 5 4 3 6 2 7
4 3 6 2 7 8 1 5
2 7 8 1 5 4 3 6
1 5 4 3 6 2 7 8
3 6 2 7 8 1 5 4
7 8 1 5 4 3 6 2
6 2 7 8 1 5 4 3
5 4 3 6 2 7 8 1
```
