import numpy as np
import gurobipy as gp
from gurobipy import GRB


def assign_tasks_to_machines(tasks, machines, machine_capacities):
    """
    Assigns tasks to machines to minimize total processing time/cost mismatch.
    
    Parameters:
    -----------
    tasks : np.ndarray
        2D array where each row represents a task with requirement metrics
        Shape: (num_tasks, num_metrics)
    
    machines : np.ndarray
        2D array where each row represents a machine with capability metrics
        Shape: (num_machines, num_metrics)
    
    machine_capacities : np.ndarray or list
        1D array of maximum tasks each machine can handle
        Shape: (num_machines,)
    
    Returns:
    --------
    np.ndarray
        2D binary matrix where result[i][j] = 1 if task i is assigned to machine j
        Shape: (num_tasks, num_machines)
    """
    tasks = np.asarray(tasks)
    machines = np.asarray(machines)
    machine_capacities = np.asarray(machine_capacities)

    assert tasks.ndim == 2 and machines.ndim == 2
    assert len(machines) == len(machine_capacities)
    assert len(tasks) <= np.sum(machine_capacities)

    env = gp.Env()
    model = gp.Model(env=env)

    n = len(tasks)  # number of tasks
    m = len(machines)  # number of machines

    # Calculate cost matrix: squared Euclidean distance between task and machine capabilities
    # This measures the mismatch between task requirements and machine capabilities
    cost = np.sum((tasks[:, np.newaxis, :] - machines[np.newaxis, :, :]) ** 2, axis=2)

    # Binary decision variables: z[i][j] = 1 if task i is assigned to machine j
    z = np.array([[model.addVar(vtype=GRB.BINARY, name=f"z{i}{j}")
                   for j in range(m)] for i in range(n)])

    # Objective: minimize total cost (mismatch between task requirements and machine capabilities)
    obj_func = gp.quicksum((cost * z).flatten())
    model.setObjective(obj_func, GRB.MINIMIZE)

    # Constraint 1: Each task must be assigned to exactly one machine
    for i in range(n):
        model.addConstr(gp.quicksum(z[i, :]) == 1, f"task_assign_{i}")

    # Constraint 2: Each machine cannot exceed its capacity
    for j in range(m):
        model.addConstr(gp.quicksum(z[:, j]) <= machine_capacities[j], f"machine_cap_{j}")

    model.params.TimeLimit = 10.0
    model.optimize()

    if model.Status == GRB.OPTIMAL or \
        (model.Status == GRB.TIME_LIMIT and model.SolCount > 0):
        return np.array([[z[i, j].X for j in range(m)] for i in range(n)])

    raise Exception(f"Optimization failed with status: {model.Status}")