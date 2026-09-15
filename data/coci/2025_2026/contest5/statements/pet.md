# Task Pet

Croatian Open Competition in Informatics — Round 5, February 21th 2026

- Time limit: 1 second
- Memory limit: 512 MiB
- Score: 110 points
- Source: [contest5_tasks.pdf](../contest5_tasks.pdf#page=5), PDF pages 5–6 (cover included).

Frog Maša is in a lake represented by a matrix with $n$ rows and $m$ columns. The cells of the matrix are marked with $0$ (water) or $1$ (water lily). From one water lily, Maša can jump to any other water lily in the same row or column. If in the previous jump Maša changed the column she was in, then in the next jump she must change the row she is in. If in the previous jump Maša changed the row she was in, then in the next jump she must change the column she is in. After Maša jumps from the water lily she is currently on, it sinks and can no longer be jumped on.

Maša likes to have fun and wants to visit a total of 5 water lilies along her path (including the starting water lily).

Help her and calculate in how many ways she can do this if she can choose any water lily as her starting point. Two paths are considered different if the positions of their first, second, third, fourth, or fifth water lilies differ.

## Input

The first line contains the natural numbers $n$ and $m$ ($1 \le n,m \le 2000$), as described in the problem statement.

In each of the following $n$ lines there are $m$ characters, which are either $0$ or $1$ and represent the cells of the lake.

## Output

Print a single number, the answer to the question from the problem statement.

## Scoring

| Subtask | Points | Constraints |
| --- | --- | --- |
| 1 | 8 | $n,m \le 4$ |
| 2 | 27 | $n,m \le 10$ |
| 3 | 58 | $n,m \le 400$ |
| 4 | 17 | No additional constraints. |

## Examples

### Example 1

Input

```text
2 3
111
110
```

Output

```text
4
```

### Example 2

Input

```text
4 4
1111
1111
1111
1111
```

Output

```text
2304
```

### Example 3

Input

```text
2 5
11110
01111
```

Output

```text
48
```

### Clarification of the first example:

The 4 possible jump paths on water lilies are:

$[1,1] \to [2,1] \to [2,2] \to [1,2] \to [1,3]$

$[1,2] \to [2,2] \to [2,1] \to [1,1] \to [1,3]$

$[1,3] \to [1,2] \to [2,2] \to [2,1] \to [1,1]$

$[1,3] \to [1,1] \to [2,1] \to [2,2] \to [1,2]$
