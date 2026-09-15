Wanting to perfect his scissors using skills, Fran came up with a new exercise. He got himself a paper strip of length $n$ centimetres and, of course, a pair of scissors. He also asked Lana to assist him for the exercise.

Lana will give Fran $k$ instructions of the following type: "Cut the $x$-th strip at $l$ centimetres". At the beginning, Fran has one strip. After the first action, he will have two strips: the first strip $l$ centimetres long, and the second one $n-l$ centimetres long (the remainder of the original strip). After that, Fran will cut either the first or the second strip - depending on Lana’s instruction. Each time he cuts a strip, the two new pieces replace the original strip in the sequence.

More formally, suppose Fran has $m$ strips of lengths $a_1,a_2,...,a_m$. If Lana tells him to cut the $x$-th strip at $l$ centimetres, the new sequence of strip lengths becomes: $a_1,a_2,...,a_{x-1},l,a_x-l,a_{x+1},...,a_m$.

After performing all cuts, he and Lana want to verify the cutting process. One way to do that is to count how many distinct strip lengths there are at the end. Your task is to compute this number.

## Input

The first line contains two natural numbers $n$ and $k$ ($2 \le n \le 500$, $1 \le k < n$), the length of the original strip and the number of instructions Lana gives Fran.

Each of the following $k$ lines contains two natural numbers $x_i$ and $l_i$ ($1 \le x_i \le i$, $1 \le l_i \le L-1$, where $L$ is the length of the $x_i$-th strip at that moment). These numbers indicate that Fran should cut the $x_i$-th strip at $l_i$ centimetres (counting strips from the beginning).

## Output

In the first and only line, write one number - the number of distinct strip lengths that Fran will be left with after he performs all the cuttings.

## Examples

### Example 1

Input

```text
5 1
1 2
```

Output

```text
2
```

### Example 2

Input

```text
6 2
1 4
1 2
```

Output

```text
1
```

### Example 3

Input

```text
10 3
1 2
2 3
3 2
```

Output

```text
2
```

### Clarification of the first example:

$[\underline{5}] \to [\underline{2,3}]$

### Clarification of the second example:

$[6] \to [\underline{4,2}] \to [4,2] \to [\underline{2,2},2]$

### Clarification of the third example:

$[10] \to [\underline{2,8}] \to [2,8] \to [2,\underline{3,5}] \to [2,3,5] \to [2,3,\underline{2,3}]$
