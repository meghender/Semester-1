Tournament Scheduler (Graph Coloring)

OverviewThis project implements an optimized Cricket Tournament Scheduling System using Graph Theory. The goal is to schedule $n$ teams such that every team plays every other team twice (Home and Away) in the minimum number of days.

The system accounts for two major constraints:
Hard Constraint: A team can play only one game every 2 days (i.e., no consecutive match days and no multiple matches on the same day).

Soft Constraint: Minimize the total duration of the tournament.FeaturesCustom ADTs: Implementation of LIST and GRAPH Abstract Data Types from scratch without using external libraries.Conflict

 Transformation: Transforms the scheduling problem into a Graph Coloring problem where nodes represent matches and edges represent scheduling conflicts.
 
 Welch-Powell Heuristic: Uses a Greedy Coloring algorithm sorted by vertex degree to approach an optimal solution.
 
 Memory Management: Explicit cleanup of pointer-based data structures to prevent memory leaks.
 Project Structure
 A1.cpp: The complete C++ source code containing ADT implementations, the graph builder, and the greedy coloring logic.
 
 report.pdf: Detailed documentation of the problem transformation and pseudocode.Setup & ExecutionPrerequisitesA C++ compiler (e.g., g++).
 
 Standard Requirement: This code is optimized for C++11 or higher to ensure compatibility with modern and slightly older compilers (like on older macOS versions).
 
CompilationOpen your terminal and run:Bashg++ -std=c++11 A1.cpp -o A1

Running the ProgramExecute the compiled file:Bash./A1

InputThe program will wait for an integer input n:

n: Number of teams participating in the tournament.

Output FormatThe program outputs the schedule day-by-day. 

If a day has no games (gap day), a blank line is printed.Matches are shown as (HomeAway).

Multiple matches on the same day are separated by ;.

Example Output (n=3):Plaintext(12)

(13)

(21)
...

Contributors
Siddharth (2025AIB2670) 
Meghender Pal (2025AIB2563) 