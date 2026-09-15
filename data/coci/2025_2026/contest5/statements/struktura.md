# Task Struktura

Croatian Open Competition in Informatics — Round 5, February 21th 2026

- Time limit: 1 second
- Memory limit: 512 MiB
- Score: 110 points
- Source: [contest5_tasks.pdf](../contest5_tasks.pdf#page=9), PDF pages 9–10 (cover included).

Petar and Ivana are bored during a long winter afternoon, so they decided to invent a game with numbers.

Petar takes a sheet of paper and randomly writes down $n$ numbers. Each number is chosen **completely at random and independently** among the integers from $1$ to $k$. Using this procedure, Petar creates an array $a$ of $n$ numbers.

Ivana says that she especially likes some arrays because they have a “hidden balance”, and she calls them structures. An array is a structure if the following conditions are satisfied:

- Every number from $1$ to $n$ appears in the array exactly once.
- For every index $i$ ($1 \le i \le n$), it holds that $|a_i+i-n-1| \le 1$.

Ivana is interested in the probability that Petar, choosing the numbers completely at random, constructs an array that is a structure.

It can be proven that the answer can always be represented as a fraction $\frac{P}{Q}$, where $P$ is an integer and $Q$ is a positive integer not divisible by $10^9+7$. In that case, output $P \cdot Q^{-1} \pmod{10^9+7}$.

## Input

The first line contains the natural numbers $n$ and $k$ ($1 \le n,k \le 10^9$), the numbers from the problem statement.

## Output

Output a single number, the answer to the question from the problem statement.

## Scoring

| Subtask | Points | Constraints |
| --- | --- | --- |
| 1 | 17 | $n,k \le 7$ |
| 2 | 23 | $n \le 7, k \le 100$ |
| 3 | 19 | $n \le 20, k \le 100$ |
| 4 | 25 | $n,k \le 10^6$ |
| 5 | 26 | No additional constraints. |

## Examples

### Example 1

Input

```text
2 1
```

Output

```text
0
```

### Example 2

Input

```text
2 2
```

Output

```text
500000004
```

### Example 3

Input

```text
7 94
```

Output

```text
100976822
```

### Clarification of the second example:

The arrays $a$ that Petar can construct are: $(1,1)$, $(1,2)$, $(2,1)$, $(2,2)$. The arrays that are structures are $(1,2)$ and $(2,1)$. The probability that Petar completely at random obtains an array that is a structure is $\frac{2}{4}$, i.e. $500000004 \pmod{10^9+7}$.
