from ortools.sat.python import cp_model
from exact_vrp import resolver
from exact_vrp.solver import _estado
from util import instancia_minima, vehiculo, punto

def test_mapeo_de_estados():
    assert _estado(cp_model.OPTIMAL) == "OPTIMO"
    assert _estado(cp_model.FEASIBLE) == "FACTIBLE"
    assert _estado(cp_model.INFEASIBLE) == "INFACTIBLE"
    assert _estado(cp_model.UNKNOWN) == "SIN_SOLUCION"

def test_infactible_del_solver_con_motivo():
    # dos puntos lejanos con la misma ventana corta y un solo camion:
    # cada uno es alcanzable por separado (pasa pre-chequeos), juntos no.
    data = instancia_minima(
        matriz_distancias_km=[[0, 10, 10], [10, 0, 200], [10, 200, 0]],
        vehiculos=[vehiculo()],
        puntos=[punto(id="a"), punto(id="b")])
    for p in data["puntos"]:
        p["ventanas"] = [{"desde": "00:10", "hasta": "00:20"}]
    sol = resolver(data)
    assert sol["estado"] == "INFACTIBLE"
    assert "ventanas" in sol["motivo"]
    assert "tiempo_solver_s" in sol
