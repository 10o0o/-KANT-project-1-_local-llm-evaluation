On the eve of an important Croatian language exam, the classroom is already prepared. We can view it as a matrix of dimension $n \times m$, where each cell represents one seat. Each cell of the matrix can have one of three values:

- 2 denotes a seat already occupied by well-behaved students. They are responsible and the teacher is not concerned about them.
- 1 denotes a seat that the teacher has marked as forbidden. No one will sit in those seats.
- 0 denotes an empty seat where mischievous students can sit.

The mischievous students have not arrived yet, but they will come soon. The teacher can decide which empty seats the mischievous students will occupy.

Well-behaved students never cheat, but they can cause mischievous students to cheat if they are adjacent to them. A mischievous student will cheat if they have at least one neighboring student (in one of the four directions: up, down, left, right), whether well-behaved or mischievous.

Determine the maximum total number of students that can be seated in the classroom (including both well-behaved and mischievous students) such that no cheating occurs during the exam.

## Input

The first line contains natural numbers $n,m$ ($1 \le n,m \le 80$), as described in the problem statement.

Each of the next $n$ lines contains $m$ characters, each being 0, 1, or 2, representing the matrix described in the problem.

## Output

In the first and only line, output a single number - the maximum total number of students that can be seated in the classroom such that no cheating occurs during the exam.

## Examples

### Example 1

Input

```text
4 4
0100
0202
1000
2120
```

Output

```text
6
```

### Example 2

Input

```text
4 4
0000
0000
0000
0000
```

Output

```text
8
```

### Clarification of the second example:

The teacher will seat students in the first and third rows in odd-numbered columns, and in the second and fourth rows in even-numbered columns. This way, she will ensure that no student can cheat.
