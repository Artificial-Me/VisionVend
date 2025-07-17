# Optimization

Optimization problems, in simple terms, are about finding the best possible solution or decision within a given set of constraints. This involves finding the maximum or minimum value of a function, representing a quantity we want to optimize, subject to certain conditions or restrictions. The derivative plays a crucial role because it helps us identify points where the rate of change of a function is zero, which oftento maximum or minimum values.

* **Objective Function:** The function we want to maximize or minimize.
* **Constraints:** Conditions or restrictions that limit the possible values of the variables.
* **Critical Points:** Points where the derivative of the objective function is zero or undefined. These are candidates for local maxima or minima.
* **Local Maximum/Minimum:** The highest/lowest point within a specific interval.
* **Global Maximum/Minimum:** The highest/lowest point over the entire domain of the function.

The first derivative of a function tells us about its slope and whether it is increasing or decreasing. At a local maximum or minimum, the slope of the function is typically zero.

* **First Derivative Test:** If the first derivative changes sign around a critical point (from positive to negative for a maximum, or negative to positive for a minimum), then that point is a local extremum.
* **Second Derivative Test:** If the second derivative of the function at a critical point is negative, the point is a local maximum. If it's positive, it's a local minimum. If it's zero, the test is inconclusive.

**Steps for Solving Optimization Problems:**

1. **Understand the Problem:** Read the problem carefully and identify what quantity needs to be optimized (maximized or minimized).
2. **Draw a Diagram (if applicable):** Visualizing the problem can help you set up the relevant relationships.
3. **Define Variables:** Assign variables to the quantities involved in the problem.
4. **Formulate the Objective Function:** Write a mathematical expression for the quantity you want to optimize, in terms of your defined variables.
5. **Formulate the Constraints:** Write mathematical equations or inequalities that represent the restrictions on the variables.
6. **Express the Objective Function in a Single Variable:** If the objective function has multiple variables, use the constraint equations to eliminate all but one variable. Determine the domain of this function based on the problem's context.
7. **Find the Critical Points:**
   * Take the first derivative of the objective function with respect to the single variable.
   * Set the derivative equal to zero and solve for the variable. These are the critical points where the slope is zero.
   * Identify points where the derivative is undefined (e.g., division by zero, square root of a negative number), as these can also be critical points.
8. **Determine Maxima/Minima:**
   * Use the First Derivative Test (checking the sign of the derivative around each critical point) or the Second Derivative Test (evaluating the second derivative at each critical point) to classify the critical points as local maxima, minima, or neither.
   * Also, evaluate the objective function at the endpoints of the domain (if the domain is a closed interval) and compare these values with the values at the critical points.
9. **State the Answer:** Clearly state the solution to the original problem, ensuring you answer the specific question asked (e.g., what are the dimensions, what is the maximum area, what is the minimum cost?). Double-check that your solution makes physical sense within the context of the problem.

# Optimization Cheat-Sheet

1. **Translate**

   - Quantity to optimize → objective f(x)
   - Everything else → constraints g(x)=0, h(x)≤0
2. **Reduce**

   - Eliminate all variables except one via constraints.
   - Record the feasible domain D (open/closed, endpoints, singularities).
3. **Probe**

   - Solve f′(x)=0 and locate f′(x) undefined → candidate set C.
   - Add boundary points of D to C.
4. **Classify**

   - First- or second-derivative test on C.
   - Evaluate f(x) on C ∪ endpoints.
   - Global extrema = max/min of this finite list.
5. **Validate**

   - Check units, physical plausibility, boundary sanity.
   - State the answer in the language of the original question.

One-liners for quick recall

- f′ flips sign → local extremum.
- f″<0 → local max; f″>0 → local min.
- Always test endpoints and discontinuities.
- If the domain is open and limits beat all critical values, no global extremum exists.

Turn a real-world “best” question into a single-variable calculus problem, then extract the global optimum and sanity-check it.
