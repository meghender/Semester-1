Disaster Relief Helicopter Routing Solver Assignment

 Overview
 
 This Assignment addresses a complex logistical optimization problem: delivering relief supplies to flooded regions using a fleet of helicopters. The goal is to maximize the total value of aid delivered (dry food, perishable food, and other supplies) to stranded villagers while minimizing operational costs and adhering to strict physical constraints.
 
 Key Constraints :
    Capacity Limits: Each helicopter has a maximum weight capacity per trip.
    Range Limits: Each helicopter has a maximum distance it can travel in a single trip ($d_{cap}$) and an overall       
                  cumulative 
    distance limit ($D_{max}$).

    Time Constraints: The solution must be computed within a specified processing time limit.
    
    Village Needs: Value is capped based on the village population (9 meals and 1 unit of supplies per person).
    
 Algorithmic ApproachThe solver implements a Simulated Annealing (SA) metaheuristic to explore the large search space of possible flight plans.
      
    Initial State: Starts with an empty solution (zero trips).
    
    Neighbor Generation: In each iteration, the solver randomly chooses between three move types:
        Add Trip: Creates a new randomized trip using a greedy nearest-neighbor approach for routing.

        Remove Trip: Removes an existing trip to explore different areas of the solution space.
        
        Swap Packages: Optimizes the payload of an existing trip by replacing lower-value items with higher-value items (e.g., swapping dry food for perishable food) if weight allows.
        
        Acceptance Criteria: Better solutions are always accepted. Worse solutions are accepted with a probability governed by the current "temperature," which cools over time, allowing the algorithm to escape local optima.
        
        Greedy Post-Processing: A final greedy pass ensures that any obviously profitable trips remaining are added before the time limit expires.
        
        File Structure
        main.cpp: Entry point for the application.
        solver.cpp / .h: Implementation of the Simulated Annealing 
        algorithm.io_handler.cpp / .h: Logic for parsing input and formatting output.
        structures.h: Definition of geometric and problem-specific data 
        structures.format_checker.cpp: A utility to verify if the output meets all problem constraints and calculate the final score.


Execution Instructions1. CompilationThe project uses a Makefile for easy compilation with g++.

Open your terminal and run:
    make

This will generate the main executable. 

To compile the format checker as well, run:
    make checker


2. Running the SolverTo execute the solver, provide the input file path and the desired output file path as arguments:
    ./main <input_filename> <output_filename>

Example: ./main input.txt output.txt3.

Verifying the SolutionTo check your generated solution for validity and see the final objective score

   ./format_checker <input_filename> <output_filename>