Skier Mia spent a day at an unusual ski resort. The resort consists of $n$ apres-ski locations (hereafter: apres) connected by slopes such that they form a connected tree rooted at the apres labeled 1. Each slope is directed from the apres with a smaller number to the apres with a larger number.

The tree is defined as follows: for each apres $i>1$, it is known from which apres $p_i$ ($p_i<i$) one arrives at it, i.e., its parent in the tree is known. This uniquely determines all slopes (slope $i$ leads to the apres labeled $i$).

During the day, Mia skied each slope exactly once and for each slope remembered its fun factor $z_i$ and speed $b_i$.

At the end of the day, Mia wants to ski down once more. Since Mia is very tired from skiing all day, she will choose a run consisting of at most $k$ consecutive slopes. The run must follow the direction of the slopes (from apres with smaller numbers to those with larger numbers). After finishing the run, a helicopter will pick her up and take her home.

For any chosen run, we define its hecticness as follows. Let:

- $z_{\mathrm{first}}$ be the fun factor of the first slope in the run
- $z_{\mathrm{last}}$ be the fun factor of the last slope in the run
- $b_i$ be the speeds of all slopes in that run

Then the hecticness of the run is: $z_{\mathrm{last}} \cdot (z_{\mathrm{last}} + \sum b_i) + z_{\mathrm{first}}^2$. In the case $k=1$, the formula remains unchanged, and $first=last$ holds.

Your task is to determine the maximum hecticness of a run that Mia can ski.

## Input

The first line contains natural numbers $n,k$ ($1 \le k \le n \le 3 \cdot 10^5$), as described in the problem statement.

The second line contains $n-1$ integers, where the $i$-th number represents from which apres one can reach the apres labeled $i+1$ ($1 \le p_i \le i$).

The third line contains $n-1$ integers, where the $i$-th number represents the fun factor of the $(i+1)$-th slope ($1 \le z_i \le 10^5$).

The fourth line contains $n-1$ integers, where the $i$-th number represents the speed of the $(i+1)$-th slope ($-10^5 \le b_i \le 10^5$).

## Output

In the first and only line, output a single number - the maximum hecticness of a run that Mia can ski.

## Examples

### Example 1

Input

```text
5 1
1 2 2 1
5 4 8 7
6 3 9 3
```

Output

```text
200
```

### Example 2

Input

```text
9 2
1 2 1 1 4 3 6 5
1 3 7 8 4 1 8 2
1 -7 -1 -6 3 8 -1 6
```

Output

```text
120
```

### Clarification of the first example:

Since $k=1$, it follows that the maximum hecticness of a run is equal to the maximum hecticness among the individual slopes. The slopes have hecticness values of 80, 44, 200, and119. The maximum hecticness is 200.
