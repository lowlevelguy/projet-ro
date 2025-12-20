import gurobipy as gp
from gurobipy import GRB
import numpy as np
from dataclasses import dataclass
from typing import List, Dict
import math


@dataclass
class Location:
    id: int
    name: str
    x: float
    y: float


@dataclass
class DemandPoint:
    id: int
    name: str
    x: float
    y: float
    demand_multiplier: float = 1.0


@dataclass
class FacilityConstraints:
    num_facilities: int
    total_area: float
    travel_cost_per_km: float
    grid_density: int = 10
    base_population: int = 100
    base_annual_visits: int = 50


class FacilityLocationSolver:
    
    def __init__(self, locations: List[Location], demand_points: List[DemandPoint], 
                 constraints: FacilityConstraints):
        self.demand_points = demand_points
        self.constraints = constraints
        if not locations:
            locations = self._generate_grid_locations()
        self.locations = locations
        self._add_grid_demand_points()
        self.model = None
        self.solution = None
        self.distances = self._calculate_distances()
    
    def _add_grid_demand_points(self):
        base_id = len(self.demand_points)
        for loc in self.locations:
            self.demand_points.append(DemandPoint(
                id=base_id,
                name=f"Grid_{loc.name}",
                x=loc.x,
                y=loc.y,
                demand_multiplier=1.0
            ))
            base_id += 1
    
    def _generate_grid_locations(self) -> List[Location]:
        side_length = math.sqrt(self.constraints.total_area)
        grid_size = self.constraints.grid_density
        step = side_length / (grid_size - 1) if grid_size > 1 else side_length
        
        locations = []
        loc_id = 0
        for i in range(grid_size):
            for j in range(grid_size):
                x = i * step
                y = j * step
                locations.append(Location(
                    id=loc_id,
                    name=f"Grid_{i}_{j}",
                    x=x,
                    y=y
                ))
                loc_id += 1
        
        return locations
        
    def _calculate_distances(self) -> np.ndarray:
        n_demand = len(self.demand_points)
        n_locations = len(self.locations)
        distances = np.zeros((n_demand, n_locations))
        
        for i, demand in enumerate(self.demand_points):
            for j, location in enumerate(self.locations):
                dx = demand.x - location.x
                dy = demand.y - location.y
                distances[i, j] = math.sqrt(dx**2 + dy**2)
        
        return distances
    
    def solve(self, time_limit: int = 300) -> Dict:
        print("Solving facility location problem...")
        
        self.model = gp.Model("FacilityLocation")
        self.model.Params.TimeLimit = time_limit
        self.model.Params.MIPGap = 0.02
        
        n_demand = len(self.demand_points)
        n_locations = len(self.locations)
        
        y = {}
        for j in range(n_locations):
            y[j] = self.model.addVar(vtype=GRB.BINARY, name=f"open_{j}")
        
        serves = {}
        for i in range(n_demand):
            for j in range(n_locations):
                serves[i, j] = self.model.addVar(vtype=GRB.BINARY, name=f"serves_{i}_{j}")
        
        total_travel_cost = gp.LinExpr()
        for i in range(n_demand):
            cost_per_km = (self.constraints.travel_cost_per_km * 
                          self.constraints.base_population *
                          self.constraints.base_annual_visits *
                          self.demand_points[i].demand_multiplier)
            for j in range(n_locations):
                total_travel_cost += cost_per_km * self.distances[i, j] * serves[i, j]
        
        self.model.setObjective(total_travel_cost, GRB.MINIMIZE)
        
        for i in range(n_demand):
            self.model.addConstr(
                gp.quicksum(serves[i, j] for j in range(n_locations)) == 1,
                name=f"serve_one_{i}"
            )
        
        for i in range(n_demand):
            for j in range(n_locations):
                self.model.addConstr(
                    serves[i, j] <= y[j],
                    name=f"serve_open_{i}_{j}"
                )
        
        self.model.addConstr(
            gp.quicksum(y[j] for j in range(n_locations)) == self.constraints.num_facilities,
            name="num_facilities"
        )
        
        self.model.optimize()
        
        if self.model.status == GRB.OPTIMAL or \
           (self.model.status == GRB.TIME_LIMIT and self.model.SolCount > 0):
            self.solution = self._extract_solution(y, serves)
            return self.solution
        else:
            return {
                "status": "infeasible", 
                "message": f"No solution found (status: {self.model.status})"
            }
    
    def _extract_solution(self, y, serves) -> Dict:
        n_demand = len(self.demand_points)
        n_locations = len(self.locations)
        
        opened_facilities = []
        
        for j in range(n_locations):
            if y[j].X > 0.5:
                loc = self.locations[j]
                opened_facilities.append({
                    'id': j,
                    'name': loc.name,
                    'x': loc.x,
                    'y': loc.y
                })
        
        assignments = []
        total_travel_cost = 0
        total_distance = 0
        
        for i in range(n_demand):
            demand = self.demand_points[i]
            
            for j in range(n_locations):
                if serves[i, j].X > 0.5:
                    nearest_dist = self.distances[i, j]
                    nearest_fac = self.locations[j]
                    
                    travel_cost = (nearest_dist * self.constraints.travel_cost_per_km * 
                                 self.constraints.base_population * self.constraints.base_annual_visits * demand.demand_multiplier)
                    
                    if demand.demand_multiplier > 1.0:
                        assignments.append({
                            'demand_point': demand.name,
                            'multiplier': demand.demand_multiplier,
                            'facility': nearest_fac.name,
                            'distance': nearest_dist
                        })
                    
                    total_travel_cost += travel_cost
                    total_distance += nearest_dist
                    break
        
        return {
            'status': 'optimal' if self.model.status == GRB.OPTIMAL else 'feasible',
            'objective_value': self.model.ObjVal,
            'num_facilities': len(opened_facilities),
            'total_travel_cost': total_travel_cost,
            'avg_distance': total_distance / n_demand if n_demand > 0 else 0,
            'opened_facilities': opened_facilities,
            'assignments': assignments,
            'solve_time': self.model.Runtime
        }
    
    def print_solution(self):
        if not self.solution:
            print("No solution available")
            return
        
        sol = self.solution
        print(f"\nStatus: {sol['status'].upper()}")
        print(f"Total travel cost: {sol['total_travel_cost']:,.2f} €")
        print(f"Facilities opened: {sol['num_facilities']}")
        print(f"Average distance: {sol['avg_distance']:.2f} km")
        print(f"Solve time: {sol['solve_time']:.2f}s")
