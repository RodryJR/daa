from ortools.sat.python import cp_model

from exact_vrp.instancia import parsear_instancia
from exact_vrp.diagnostico import diagnosticar
from exact_vrp.modelo import construir_modelo

_ESTADOS = {cp_model.OPTIMAL: "OPTIMO", cp_model.FEASIBLE: "FACTIBLE",
            cp_model.INFEASIBLE: "INFACTIBLE"}


def _estado(status):
    return _ESTADOS.get(status, "SIN_SOLUCION")


def resolver(data):
    inst = parsear_instancia(data)
    errores = diagnosticar(inst)
    if errores:
        return {"estado": "INFACTIBLE", "motivo": "; ".join(errores)}

    m = construir_modelo(inst)
    m.model.Minimize(m.costo_cent)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = inst.limite_solver_s
    solver.parameters.num_workers = 8
    status = solver.Solve(m.model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        salida = {"estado": _estado(status)}
        if salida["estado"] == "INFACTIBLE":
            salida["motivo"] = ("sin solucion que cumpla todas las restricciones "
                               "(combinacion de ventanas, turnos y flota)")
        return salida
    return _extraer(inst, m, solver, status)


def _extraer(inst, m, solver, status):
    rutas, sin_usar = [], []
    combustible = 0.0
    fijos = 0.0
    salarios_km = 0.0
    for iv, v in enumerate(inst.vehiculos):
        if not solver.Value(m.usado[iv]):
            sin_usar.append(v.id)
            continue
        orden, km = [], 0.0
        nodo = 0
        while True:
            siguiente = next(j for j in range(len(inst.puntos) + 1)
                             if j != nodo and solver.Value(m.x[iv, nodo, j]))
            km += inst.dist_km[nodo][siguiente]
            if siguiente == 0:
                break
            orden.append(siguiente)
            nodo = siguiente
        litros = km * v.consumo_litros_km
        combustible += litros * inst.precio_litro
        fijos += v.salario_fijo_cent / 100
        salarios_km += km * v.salario_por_km
        rutas.append({
            "vehiculo": v.id,
            "paradas": [{"punto": inst.puntos[p - 1].id} for p in orden],
            "km": round(km, 2), "litros": round(litros, 2),
            "costo": round(km * (v.consumo_litros_km * inst.precio_litro + v.salario_por_km)
                           + v.salario_fijo_cent / 100, 2),
        })
    objetivo = solver.ObjectiveValue()
    gap = 0.0 if status == cp_model.OPTIMAL or objetivo == 0 else round(
        abs(objetivo - solver.BestObjectiveBound()) / objetivo, 4)
    return {
        "estado": _estado(status),
        "gap_relativo": gap,
        "costo_total": round(objetivo / 100, 2),
        "desglose": {"combustible": round(combustible, 2), "salarios_fijos": round(fijos, 2),
                     "salarios_km": round(salarios_km, 2), "salarios_horas": 0.0},
        "rutas": rutas,
        "vehiculos_sin_usar": sin_usar,
        "tiempo_solver_s": round(solver.WallTime(), 2),
    }
