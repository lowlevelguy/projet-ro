import gurobipy as gp
from gurobipy import GRB
import itertools
from dataclasses import dataclass
from typing import List, Tuple, Dict

@dataclass
class Piece:
    """Représente une pièce à découper"""
    id: int
    width: float
    height: float
    demand: int
    priority: int  # 1=haute, 2=moyenne, 3=basse
    name: str = ""

@dataclass
class PlateType:
    """Représente un type de plaque brute"""
    id: int
    width: float
    height: float
    cost: float
    max_available: int
    quality_level: int  # 1=premium, 2=standard, 3=économique
    name: str = ""

@dataclass
class Pattern:
    """Représente un motif de découpe sur une plaque"""
    plate_type_id: int
    pieces_count: Dict[int, int]  # {piece_id: quantité}
    waste: float
    
class CuttingStockSolver:
    """Solveur pour le problème de découpe 2D"""
    
    def __init__(self, pieces: List[Piece], plate_types: List[PlateType], 
                 allow_rotation: bool = True, max_patterns_per_plate: int = 1000):
        self.pieces = pieces
        self.plate_types = plate_types
        self.allow_rotation = allow_rotation
        self.max_patterns_per_plate = max_patterns_per_plate
        self.patterns: List[Pattern] = []
        self.model = None
        self.solution = None
        
    def generate_patterns(self) -> int:
        """Génère tous les motifs de découpe réalisables"""
        print("Génération des motifs de découpe...")
        total_patterns = 0
        
        for plate in self.plate_types:
            plate_patterns = self._generate_patterns_for_plate(plate)
            self.patterns.extend(plate_patterns)
            total_patterns += len(plate_patterns)
            print(f"  Plaque {plate.name}: {len(plate_patterns)} motifs générés")
        
        print(f"Total: {total_patterns} motifs générés\n")
        return total_patterns
    
    def _generate_patterns_for_plate(self, plate: PlateType) -> List[Pattern]:
        """Génère les motifs pour un type de plaque donné"""
        patterns = []
        
        # Pour chaque pièce, calculer combien on peut en mettre (sans rotation)
        for piece in self.pieces:
            # Contrainte de qualité: pièces prioritaires sur plaques premium uniquement
            if piece.priority == 1 and plate.quality_level > 1:
                continue
            
            orientations = [(piece.width, piece.height)]
            if self.allow_rotation and piece.width != piece.height:
                orientations.append((piece.height, piece.width))
            
            for w, h in orientations:
                if w <= plate.width and h <= plate.height:
                    nx = int(plate.width // w)
                    ny = int(plate.height // h)
                    max_pieces = min(nx * ny, piece.demand * 2)  # Limite raisonnable
                    
                    # Créer des motifs avec différentes quantités
                    for n in range(1, max_pieces + 1):
                        waste = (plate.width * plate.height) - (n * w * h)
                        waste_pct = waste / (plate.width * plate.height)
                        
                        # Ne garder que les motifs avec chute < 70%
                        if waste_pct < 0.7:
                            pattern = Pattern(
                                plate_type_id=plate.id,
                                pieces_count={piece.id: n},
                                waste=waste
                            )
                            patterns.append(pattern)
        
        # Générer quelques motifs combinés (2 types de pièces différentes)
        if len(self.pieces) > 1:
            for piece1, piece2 in itertools.combinations(self.pieces, 2):
                # Vérifier compatibilité de qualité
                if piece1.priority == 1 and plate.quality_level > 1:
                    continue
                if piece2.priority == 1 and plate.quality_level > 1:
                    continue
                    
                patterns.extend(self._generate_combined_patterns(
                    plate, piece1, piece2
                ))
        
        return patterns[:self.max_patterns_per_plate]
    
    def _generate_combined_patterns(self, plate: PlateType, 
                                    piece1: Piece, piece2: Piece) -> List[Pattern]:
        """Génère des motifs combinant deux types de pièces"""
        combined = []
        
        for n1 in range(1, min(4, piece1.demand + 1)):
            for n2 in range(1, min(4, piece2.demand + 1)):
                # Essayer différentes orientations
                for w1, h1 in [(piece1.width, piece1.height), 
                               (piece1.height, piece1.width)] if self.allow_rotation else [(piece1.width, piece1.height)]:
                    for w2, h2 in [(piece2.width, piece2.height), 
                                   (piece2.height, piece2.width)] if self.allow_rotation else [(piece2.width, piece2.height)]:
                        
                        # Arrangement horizontal
                        total_w = n1 * w1 + n2 * w2
                        total_h = max(h1, h2)
                        
                        if total_w <= plate.width and total_h <= plate.height:
                            waste = (plate.width * plate.height) - (n1*w1*h1 + n2*w2*h2)
                            combined.append(Pattern(
                                plate_type_id=plate.id,
                                pieces_count={piece1.id: n1, piece2.id: n2},
                                waste=waste
                            ))
        
        return combined
    
    def solve(self, time_limit: int = 300) -> Dict:
        """Résout le problème d'optimisation avec Gurobi"""
        print("Construction du modèle d'optimisation...")
        
        # Créer le modèle
        self.model = gp.Model("CuttingStock2D")
        self.model.Params.TimeLimit = time_limit
        self.model.Params.MIPGap = 0.01  # 1% d'optimalité
        
        # Variables de décision: x[j] = nombre de fois qu'on utilise le motif j
        x = {}
        for j, pattern in enumerate(self.patterns):
            x[j] = self.model.addVar(vtype=GRB.INTEGER, lb=0, name=f"x_{j}")
        
        # Fonction objectif: Minimiser le coût total (multi-critère)
        # Critère 1: Coût des plaques (poids: 100)
        # Critère 2: Chute totale (poids: 1)
        # Critère 3: Nombre de plaques (poids: 10)
        cost_expr = gp.LinExpr()
        waste_expr = gp.LinExpr()
        plates_expr = gp.LinExpr()
        
        for j, pattern in enumerate(self.patterns):
            plate = next(p for p in self.plate_types if p.id == pattern.plate_type_id)
            cost_expr += plate.cost * x[j]
            waste_expr += pattern.waste * x[j]
            plates_expr += x[j]
        
        self.model.setObjective(
            100 * cost_expr + 1 * waste_expr + 10 * plates_expr,
            GRB.MINIMIZE
        )
        
        print("Ajout des contraintes...")
        
        # CONTRAINTE 1: Satisfaction de la demande pour chaque pièce
        for piece in self.pieces:
            demand_expr = gp.LinExpr()
            for j, pattern in enumerate(self.patterns):
                if piece.id in pattern.pieces_count:
                    demand_expr += pattern.pieces_count[piece.id] * x[j]
            self.model.addConstr(
                demand_expr >= piece.demand,
                name=f"demand_piece_{piece.id}"
            )
        
        # CONTRAINTE 2: Limite de plaques disponibles par type
        for plate in self.plate_types:
            plates_used = gp.LinExpr()
            for j, pattern in enumerate(self.patterns):
                if pattern.plate_type_id == plate.id:
                    plates_used += x[j]
            self.model.addConstr(
                plates_used <= plate.max_available,
                name=f"max_plates_type_{plate.id}"
            )
        
        # CONTRAINTE 3: Pièces prioritaires sur plaques premium (qualité)
        # (Déjà intégrée dans la génération de motifs)
        
        # CONTRAINTE 4: Limiter la sur-production (max 10% au-dessus de la demande)
        for piece in self.pieces:
            production_expr = gp.LinExpr()
            for j, pattern in enumerate(self.patterns):
                if piece.id in pattern.pieces_count:
                    production_expr += pattern.pieces_count[piece.id] * x[j]
            self.model.addConstr(
                production_expr <= piece.demand * 1.1,
                name=f"max_production_piece_{piece.id}"
            )
        
        # CONTRAINTE 5: Équilibrage entre types de plaques (utilisation raisonnable)
        # Au moins 20% de l'utilisation totale pour chaque type disponible
        total_plates = gp.quicksum(x[j] for j in range(len(self.patterns)))
        for plate in self.plate_types:
            if plate.max_available > 0:
                plates_of_type = gp.quicksum(
                    x[j] for j, p in enumerate(self.patterns) 
                    if p.plate_type_id == plate.id
                )
                # Cette contrainte assure une diversification
                self.model.addConstr(
                    plates_of_type >= 0.05 * total_plates,
                    name=f"balance_plate_type_{plate.id}"
                )
        
        print(f"\nModèle construit:")
        print(f"  - Variables: {self.model.NumVars}")
        print(f"  - Contraintes: {self.model.NumConstrs}")
        print(f"\nRésolution en cours...\n")
        
        # Résoudre
        self.model.optimize()
        
        # Extraire la solution
        if self.model.status == GRB.OPTIMAL or self.model.status == GRB.TIME_LIMIT:
            self.solution = self._extract_solution(x)
            return self.solution
        else:
            return {"status": "infeasible", "message": "Aucune solution trouvée"}
    
    def _extract_solution(self, x) -> Dict:
        """Extrait les résultats de la solution"""
        used_patterns = []
        total_cost = 0
        total_waste = 0
        total_plates = 0
        plates_by_type = {p.id: 0 for p in self.plate_types}
        pieces_produced = {p.id: 0 for p in self.pieces}
        
        for j, pattern in enumerate(self.patterns):
            if x[j].X > 0.5:  # Variable entière
                count = int(round(x[j].X))
                plate = next(p for p in self.plate_types if p.id == pattern.plate_type_id)
                
                used_patterns.append({
                    'pattern_id': j,
                    'plate_type': plate.name,
                    'plate_cost': plate.cost,
                    'count': count,
                    'pieces': pattern.pieces_count,
                    'waste_per_plate': pattern.waste
                })
                
                total_cost += plate.cost * count
                total_waste += pattern.waste * count
                total_plates += count
                plates_by_type[plate.id] += count
                
                for piece_id, qty in pattern.pieces_count.items():
                    pieces_produced[piece_id] += qty * count
        
        return {
            'status': 'optimal' if self.model.status == GRB.OPTIMAL else 'feasible',
            'objective_value': self.model.ObjVal,
            'total_cost': total_cost,
            'total_waste': total_waste,
            'total_plates': total_plates,
            'plates_by_type': plates_by_type,
            'pieces_produced': pieces_produced,
            'used_patterns': used_patterns,
            'solve_time': self.model.Runtime
        }
    
    def print_solution(self):
        """Affiche la solution de manière lisible"""
        if not self.solution:
            print("Aucune solution disponible")
            return
        
        print("\n" + "="*60)
        print("SOLUTION OPTIMALE" if self.solution['status'] == 'optimal' else "SOLUTION RÉALISABLE")
        print("="*60)
        
        print(f"\nCoût total: {self.solution['total_cost']:.2f} €")
        print(f"Chute totale: {self.solution['total_waste']:.2f} unités²")
        print(f"Nombre de plaques: {self.solution['total_plates']}")
        print(f"Temps de résolution: {self.solution['solve_time']:.2f} secondes")
        
        print("\n--- Plaques utilisées par type ---")
        for plate in self.plate_types:
            count = self.solution['plates_by_type'][plate.id]
            if count > 0:
                print(f"  {plate.name}: {count} plaque(s)")
        
        print("\n--- Production par pièce ---")
        for piece in self.pieces:
            produced = self.solution['pieces_produced'][piece.id]
            print(f"  {piece.name}: {produced}/{piece.demand} (demande)")
        
        print("\n--- Détail des motifs utilisés ---")
        for pattern in self.solution['used_patterns']:
            print(f"\n  Motif #{pattern['pattern_id']} - {pattern['plate_type']} x{pattern['count']}")
            pieces_desc = ", ".join([
                f"{self._get_piece_name(pid)}×{qty}" 
                for pid, qty in pattern['pieces'].items()
            ])
            print(f"    Pièces: {pieces_desc}")
            print(f"    Chute: {pattern['waste_per_plate']:.2f} unités²/plaque")
        
        print("\n" + "="*60 + "\n")
    
    def _get_piece_name(self, piece_id: int) -> str:
        """Récupère le nom d'une pièce par son ID"""
        for piece in self.pieces:
            if piece.id == piece_id:
                return piece.name
        return f"Pièce {piece_id}"