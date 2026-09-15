The chef at the most famous restaurant in Poland is preparing tomahawk steaks for a group of young and cheerful (and very hungry) programmers!

The steak can be represented as an $n \times n$ matrix. Initially, the temperature of the whole steak is 0 degrees. During the cooking process, the temperature in different parts of the steak (i.e., different cells in the matrix) will increase.

In order to prepare the perfect tomahawk steak, the chef lifts the steak and puts it back on the grill $q$ times. Each time, the chef can place the steak on one of three sides: left, right, or down. He will then let the steak cook on that side for $x$ seconds.

When the steak is being baked on its down side, it can be baked for at most $n$ seconds. After this, the temperature of all the cells in the $n$-th row in the matrix will increase by $x$, the temperature of the cells in the $n-1$-st row will increase by $x-1$, the temperature of the $n-2$-nd row will increase by $x-2$, ..., the temperature of the cells in row number $n-x+1$ will increase by 1.

When the tomahawk steak is being baked on its right side, it can be baked for at most $\lfloor \frac{n+1}{2} \rfloor$ seconds. After this, the temperature of all the cells in the $n$-th column in the matrix will increase by $x$, the temperature of the cells in the $n-1$-st column will increase by $x-1$, the temperature of the $n-2$-nd column will increase by $x-2$, ..., the temperature of the cells in column number $n-x+1$ will increase by 1.

Similarly, when the tomahawk steak is being baked on its left side, it can be baked for at most $\lfloor \frac{n+1}{2} \rfloor$ seconds. After this, the temperature of all the cells in the first column in the matrix will increase by $x$, the temperature of the cells in the second column will increase by $x-1$, the temperature of the third column will increase by $x-2$, ..., the temperature of the cells in column number $x$ will increase by 1.

We know that the tastiness of the tomahawk is closely related to the contrast of temperatures, that’s why the chef wants to find out the difference between the coldest and the hottest part of the steak!

## Input

In the first line, there are two natural numbers $n$ and $q$ ($1 \le n \le 10^9$, $1 \le q \le 10^5$), the size of the steak and the number of times the chef lifts the steak.

In each of the following $q$ lines, there is a single letter $s$ and a natural number $x$. The letter $s$ indicates the side of the tomahawk steak: "L" – left, "R" – right, or "D" – down. If $s = \text{”D”}$, then $1 \le x \le n$. Otherwise, $1 \le x \le \lfloor \frac{n+1}{2} \rfloor$.

## Output

In the first and only line, print a single number - the difference in degrees between the coldest and hottest cell on the steak.

## Examples

### Example 1

Input

```text
4 2
L 2
R 1
```

Output

```text
2
```

### Example 2

Input

```text
3 3
R 2
D 3
R 2
```

Output

```text
6
```

### Clarification of the first example:

$$
\begin{bmatrix}
0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0 \\
0 & 0 & 0 & 0
\end{bmatrix}
\to
\begin{bmatrix}
2 & 1 & 0 & 0 \\
2 & 1 & 0 & 0 \\
2 & 1 & 0 & 0 \\
2 & 1 & 0 & 0
\end{bmatrix}
\to
\begin{bmatrix}
2 & 1 & 0 & 1 \\
2 & 1 & 0 & 1 \\
2 & 1 & 0 & 1 \\
2 & 1 & 0 & 1
\end{bmatrix}
$$

### Clarification of the second example:

$$
\begin{bmatrix}
0 & 0 & 0 \\
0 & 0 & 0 \\
0 & 0 & 0
\end{bmatrix}
\to
\begin{bmatrix}
0 & 1 & 2 \\
0 & 1 & 2 \\
0 & 1 & 2
\end{bmatrix}
\to
\begin{bmatrix}
1 & 2 & 3 \\
2 & 3 & 4 \\
3 & 4 & 5
\end{bmatrix}
\to
\begin{bmatrix}
1 & 3 & 5 \\
2 & 4 & 6 \\
3 & 5 & 7
\end{bmatrix}
$$
