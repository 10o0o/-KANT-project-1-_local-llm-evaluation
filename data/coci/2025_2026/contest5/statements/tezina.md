Strong Karlo is in the gym. An array $a$ of $n$ numbers is given, where each number represents the weight of one item in front of Karlo. An integer $k$ is also given, representing the number of different weights Karlo can use.

For each weight type from $1$ to $k$ and for each item in the array, Karlo does the following:

1. Divide the item’s weight by the weight type and record the **integer part of the division** (discard the fractional part).
2. Multiply the obtained integer by the item’s weight increased by $2$. If the resulting number is greater than $10^8$, Karlo replaces it with $10^8$.
3. Sum all obtained numbers for that weight type. The obtained sum is called the **strength** of that weight type.

Karlo is interested in the sum of strengths of all weight types in the gym. Since Karlo does not have time to calculate it, help him solve his problem.

## Input

The first line contains the natural numbers $n$ and $k$ ($1 \le n,k \le 10^5$), the number of items in front of Karlo and the number of weight types Karlo can use.

The second line contains an array of $n$ numbers ($1 \le a_i \le 10^5$), the weights of the items in front of Karlo.

## Output

Print a single number, the answer to the question from the problem statement.

## Examples

### Example 1

Input

```text
1 2
2
```

Output

```text
12
```

### Example 2

Input

```text
2 1
3 4
```

Output

```text
39
```

### Example 3

Input

```text
7 19
1 2 3 4 5 6 7
```

Output

```text
414
```

### Clarification of the second example:

Karlo will transform the number 3 into $3 \cdot 5=15$, and the number 4 into $4 \cdot 6=24$. Their sum equals 39.
