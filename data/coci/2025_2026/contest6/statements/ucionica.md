A group of $k$ friends enters a classroom. The height $h_i$ of each friend is known, and the heights of all other students already in the classroom are also known.

The classroom can be represented as an $n \times m$ grid $a$, where each cell corresponds to a seat. The seat in the $i$-th row and $j$-th column is denoted by $a_{i,j}$. For every seat, we know whether it is already occupied by a student (along with their height) or if it is empty.

The $k$ friends want to take seats in the classroom. Each friend occupies exactly one empty seat, and no two friends can sit in the same seat. Additionally, they want to sit next to each other in the same row. More precisely, they choose a row index $i$ such that $1 \le i \le n$ and a column index $j$ such that $1 \le j \le m-k+1$, and sit in the seats $a_{i,j},a_{i,j+1},\ldots,a_{i,j+k-1}$. The friends can sit in these seats in any order; they do not have to sit in the order in which their heights were given.

A friend considers a seat suitable only if all students sitting in front of them (i.e., in rows with a smaller index in the same column) are strictly shorter than them, ensuring they have a clear view. The group considers a set of $k$ consecutive seats in the same row suitable if they can arrange themselves so that each friend has a clear view.

Considering these conditions, how many suitable sets of seats for the group are there in the classroom?

## Input

The first line contains three natural numbers $n$, $m$, and $k$ ($1 \le n,m \le 2000$, $1 \le k \le m$) - the number of rows and columns of the classroom and the number of friends.

The second line contains $k$ natural numbers $h_1,h_2,\ldots,h_k$ - the heights of the friends.

The next $n$ lines each contain $m$ natural numbers: if $a_{i,j}=0$, the seat is empty, and if $a_{i,j} \ge 1$, the seat is occupied by a student of height $a_{i,j}$ ($1 \le a_{i,j} \le 10^9$).

## Output

In the first and only line, output a single number - the number of suitable sets of $k$ consecutive seats in the same row where the friends can be arranged so that each has a clear view.

## Examples

### Example 1

Input

```text
3 4 2
2 6
0 0 3 1
8 0 0 0
0 0 1 0
```

Output

```text
3
```

### Example 2

Input

```text
2 4 4
5 2 4 3
1 2 3 4
0 0 0 0
```

Output

```text
1
```

### Example 3

Input

```text
5 5 3
17 3 17
0 0 0 0 0
0 0 0 0 0
0 0 0 0 0
0 0 0 0 0
0 0 0 0 0
```

Output

```text
15
```

### Clarification of the first example:

The two friends can sit in the first and second seats in the first row, in the second and third seats in the second row, or in the third and fourth seats in the second row. So, they can sit in a total of 3 different sets of seats.

### Clarification of the second example:

The four friends can sit in the only four available seats if they arrange themselves from shortest to tallest.

### Clarification of the third example:

The three friends can sit in any three consecutive seats in the same row since there are no other students in the classroom resulting in a total of 15 valid sitting arrangements.
