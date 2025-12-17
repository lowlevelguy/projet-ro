import numpy as np
import gurobipy as gp
from gurobipy import GRB
import pandas as pd

def solve_cutting_stock(L, lengths, demands, max_width=None):
    """
    Résout le problème de découpe avec contrainte de largeur.
    
    Args:
        L: Longueur du matériau brut (float)
        lengths: Liste des longueurs des pièces (list of float)
        demands: Liste des demandes (list of int)
        max_width: Largeur maximale (pièces par motif) (int, optional)
    
    Returns:
        dict: Résultats de l'optimisation
    """
    m = len(lengths)
    
    # Génération des motifs valides
    patterns = []
    
    # Fonction de validation
    def is_valid(pattern):
        total_length = sum(lengths[i] * pattern[i] for i in range(m))
        total_pieces = sum(pattern)
        return total_length <= L and (max_width is None or total_pieces <= max_width)
    
    # Génération des motifs
    # 1. Motifs à une pièce
    for i in range(m):
        max_i = int(L // lengths[i])
        for cnt in range(1, max_i + 1):
            pattern = [0] * m
            pattern[i] = cnt
            if is_valid(pattern):
                patterns.append(pattern)
    
    # 2. Combinaisons de 2 pièces
    if m >= 2:
        for i in range(m):
            for j in range(i + 1, m):
                max_i = int(L // lengths[i])
                for cnt_i in range(1, max_i + 1):
                    remaining = L - cnt_i * lengths[i]
                    max_j = int(remaining // lengths[j])
                    for cnt_j in range(1, max_j + 1):
                        pattern = [0] * m
                        pattern[i] = cnt_i
                        pattern[j] = cnt_j
                        if is_valid(pattern):
                            patterns.append(pattern)
    
    # Modèle Gurobi
    model = gp.Model()
    x = [model.addVar(vtype=GRB.CONTINUOUS, lb=0) for _ in range(len(patterns))]
    
    # Objectif : minimiser le nombre de matériaux
    model.setObjective(gp.quicksum(x), GRB.MINIMIZE)
    
    # Contraintes de demande
    for i in range(m):
        model.addConstr(
            gp.quicksum(patterns[j][i] * x[j] for j in range(len(patterns))) >= demands[i]
        )
    
    model.setParam('OutputFlag', 0)
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        # Calcul des résultats
        used_patterns = []
        total_material = 0
        total_waste = 0
        
        for j in range(len(patterns)):
            if x[j].X > 1e-6:
                pattern = patterns[j]
                amount = x[j].X
                waste_per_unit = L - sum(lengths[i] * pattern[i] for i in range(m))
                waste_total = waste_per_unit * amount
                
                used_patterns.append({
                    'pattern': pattern,
                    'amount': amount,
                    "waste_per_unit": waste_per_unit,  # CHANGÉ ICI
                    "waste_total": waste_total         # CHANGÉ ICI
                })
                total_material += amount
                total_waste += waste_total
        
        utilization = 1 - (total_waste / (total_material * L)) if total_material > 0 else 0
        
        return {
            'status': 'OPTIMAL',
            'total_material': total_material,
            'total_waste': total_waste,
            'utilization': utilization,
            'patterns_generated': len(patterns),
            'patterns_used': len(used_patterns),
            'solution': used_patterns
        }
    
    return {'status': 'FAILED'}