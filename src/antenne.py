import math

import gurobipy as gp
import numpy as np
from gurobipy import GRB


def solve_set_covering(width, height, antennas, max_budget):
    max_radius = max(antenna[0] for antenna in antennas)
    spacing = max_radius / 2

    x_positions = np.arange(0, width + spacing, spacing)
    y_positions = np.arange(0, height + spacing, spacing)

    candidates = [
        (x, y)
        for x in x_positions
        for y in y_positions
        if 0 <= x <= width and 0 <= y <= height
    ]

    min_radius = min(antenna[0] for antenna in antennas)
    demand_spacing = min_radius / 6
    demand_x = np.arange(0, width + demand_spacing, demand_spacing)
    demand_y = np.arange(0, height + demand_spacing, demand_spacing)
    demand_points = [
        (x, y)
        for x in demand_x
        for y in demand_y
        if 0 <= x <= width and 0 <= y <= height
    ]

    coverage = {}
    for i, candidate in enumerate(candidates):
        coverage[i] = {}
        for a, (radius, _) in enumerate(antennas):
            coverage[i][a] = []
            for j, demand in enumerate(demand_points):
                dist = math.sqrt(
                    (candidate[0] - demand[0]) ** 2 + (candidate[1] - demand[1]) ** 2
                )
                if dist <= radius:
                    coverage[i][a].append(j)

    model = gp.Model("multi_antenna_set_covering")
    model.setParam("OutputFlag", 0)

    x = model.addVars(len(candidates), len(antennas), vtype=GRB.BINARY, name="x")

    model.setObjective(
        gp.quicksum(
            x[i, a] * antennas[a][1]
            for i in range(len(candidates))
            for a in range(len(antennas))
        ),
        GRB.MINIMIZE,
    )

    for j in range(len(demand_points)):
        covering_antennas = [
            (i, a)
            for i in range(len(candidates))
            for a in range(len(antennas))
            if j in coverage[i][a]
        ]
        if covering_antennas:
            model.addConstr(
                gp.quicksum(x[i, a] for i, a in covering_antennas) >= 1,
                name=f"cover_{j}",
            )

    for i in range(len(candidates)):
        model.addConstr(
            gp.quicksum(x[i, a] for a in range(len(antennas))) <= 1,
            name=f"single_antenna_{i}",
        )

    model.addConstr(
        gp.quicksum(
            x[i, a] * antennas[a][1]
            for i in range(len(candidates))
            for a in range(len(antennas))
        )
        <= max_budget,
        name="budget",
    )

    interference_count = 0
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            dist_ij = math.sqrt(
                (candidates[i][0] - candidates[j][0]) ** 2
                + (candidates[i][1] - candidates[j][1]) ** 2
            )

            for a in range(len(antennas)):
                for b in range(len(antennas)):
                    min_distance = 0.5 * (antennas[a][0] + antennas[b][0])

                    if dist_ij < min_distance:
                        model.addConstr(
                            x[i, a] + x[j, b] <= 1, name=f"interference_{i}_{a}_{j}_{b}"
                        )
                        interference_count += 1

    model.optimize()

    selected_positions = []
    if model.Status == GRB.OPTIMAL:
        for i in range(len(candidates)):
            for a in range(len(antennas)):
                if x[i, a].X > 0.5:
                    selected_positions.append((candidates[i][0], candidates[i][1], a))

        total_cost = sum(antennas[a][1] for _, _, a in selected_positions)
        print(f"Optimal solution found!")
        print(f"Total antennas placed: {len(selected_positions)}")
        print(f"Total cost: {total_cost:.2f} (Budget: {max_budget:.2f})")
        for a in range(len(antennas)):
            count = sum(
                1 for _, _, antenna_type in selected_positions if antenna_type == a
            )
            if count > 0:
                print(
                    f"  Antenna type {a} (radius={antennas[a][0]}, price={antennas[a][1]}): {count} units"
                )
    elif model.Status == GRB.INFEASIBLE:
        print(
            "No feasible solution found! The budget may be too low to cover the area."
        )
    else:
        print(f"Optimization ended with status: {model.Status}")

    return selected_positions
