import numpy as np
import gurobipy as gp
from gurobipy import GRB


def assign_tasks_to_machines(task_names, machine_capacities, task_conflicts=None):
    """
    Assigns tasks to machines respecting capacity and conflict constraints.
    This is a graph coloring problem with capacity constraints.
    
    Parameters:
    -----------
    task_names : list
        List of task names/identifiers
        Example: ['Task_1', 'Task_2', 'Task_3']
    
    machine_capacities : dict or list
        Machine capacities (max tasks each can handle)
        If dict: {'Machine_A': 2, 'Machine_B': 3}
        If list: [2, 3, 2] → machines named Machine_0, Machine_1, etc.
    
    task_conflicts : np.ndarray, optional
        2D binary matrix where task_conflicts[i][j] = 1 if tasks i and j cannot be done simultaneously.
        If None, no conflicts are considered.
        Shape: (num_tasks, num_tasks)
    
    Returns:
    --------
    dict
        Dictionary mapping task names to assigned machine indices
        Example: {'Task_1': 0, 'Task_2': 1, 'Task_3': 0}
    """
    # Convert machine_capacities to dict if it's a list
    if isinstance(machine_capacities, (list, np.ndarray)):
        machine_capacities = {f'Machine_{i}': cap for i, cap in enumerate(machine_capacities)}
    
    n = len(task_names)  # number of tasks
    m = len(machine_capacities)  # number of machines
    
    # If task_conflicts is not provided, create empty conflict matrix
    if task_conflicts is None:
        task_conflicts = np.zeros((n, n), dtype=int)
    else:
        task_conflicts = np.asarray(task_conflicts)
        assert task_conflicts.ndim == 2
        assert task_conflicts.shape == (n, n)
    
    env = gp.Env()
    model = gp.Model(env=env)
    
    # Binary decision variables: z[i][j] = 1 if task i is assigned to machine j
    z = np.array([[model.addVar(vtype=GRB.BINARY, name=f"z_{task_names[i]}_{j}")
                   for j in range(m)] for i in range(n)])
    
    # Objective: This is a feasibility problem, so we can set a dummy objective
    model.setObjective(0, GRB.MINIMIZE)
    
    # Constraint 1: Each task must be assigned to exactly one machine
    for i in range(n):
        model.addConstr(gp.quicksum(z[i, :]) == 1, f"task_assign_{task_names[i]}")
    
    # Constraint 2: Each machine cannot exceed its capacity
    capacities = list(machine_capacities.values())
    for j in range(m):
        model.addConstr(gp.quicksum(z[:, j]) <= capacities[j], f"machine_cap_{j}")
    
    # Constraint 3: Conflicting tasks cannot be assigned to the same machine
    for i in range(n):
        for k in range(i + 1, n):
            if task_conflicts[i, k] == 1 or task_conflicts[k, i] == 1:
                for j in range(m):
                    model.addConstr(z[i, j] + z[k, j] <= 1, f"conflict_{i}_{k}_machine_{j}")
    
    model.params.TimeLimit = 10.0
    model.optimize()
    
    if model.Status == GRB.OPTIMAL or \
        (model.Status == GRB.TIME_LIMIT and model.SolCount > 0):
        # Extract solution
        result = {}
        for i in range(n):
            for j in range(m):
                if z[i, j].X > 0.5:
                    result[task_names[i]] = j
                    break
        return result
    
    raise Exception(f"Optimization failed with status: {model.Status}")