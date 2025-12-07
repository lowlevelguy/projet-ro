import numpy as np
import gurobipy as gp
from gurobipy import GRB

# def dist_squared(x : list, y : list):
#     assert len(x) == len(y)
#     
#     n = len(x)
#     dist_sq = 0
#     for i in range(n):
#         dist_sq += (x[i]-y[i])**2
#     return dist_sq

def affect_interns(students, internships, internship_capacities):
    students = np.asarray(students)
    internships = np.asarray(internships)
    internship_capacities = np.asarray(internship_capacities)

    assert students.ndim == 2 and internships.ndim == 2
    assert len(internships) == len(internship_capacities)
    assert len(students) <= np.sum(internship_capacities)

    env = gp.Env()
    model = gp.Model(env=env)

    n = len(students)
    m = len(internships)

    d = np.sum((students[:, np.newaxis, :] - internships[np.newaxis, :, :]) ** 2, axis=2)

    z = np.array([[model.addVar(vtype=GRB.BINARY, name=f"z{i}{j}")
                   for j in range(m)] for i in range(n)])

    obj_func = gp.quicksum((d * z).flatten())
    model.setObjective(obj_func, GRB.MINIMIZE)

    for i in range(n):
        model.addConstr(gp.quicksum(z[i, :]) == 1, f"aff{i}")

    for j in range(m):
        model.addConstr(gp.quicksum(z[:, j]) <= internship_capacities[j], f"cap{j}")

    model.params.TimeLimit = 10.0
    model.optimize()

    if model.Status == GRB.OPTIMAL or \
        (model.Status == GRB.TIME_LIMIT and model.SolCount > 0):
        return np.array([[z[i, j].X for j in range(m)] for i in range(n)])

    raise Exception(f"Optimization failed with status: {model.Status}")

