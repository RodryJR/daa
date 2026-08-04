from ortools.sat.python import cp_model

from exact_vrp.instancia import DIAS, MINUTOS_DIA, parsear_instancia
from exact_vrp.diagnostico import diagnosticar
from exact_vrp.modelo import construir_modelo

_ESTADOS = {cp_model.OPTIMAL: "OPTIMO", cp_model.FEASIBLE: "FACTIBLE",
            cp_model.INFEASIBLE: "INFACTIBLE"}


def _estado(status):
    return _ESTADOS.get(status, "SIN_SOLUCION")


def _momento(minuto, modo):
    hora = f"{(minuto % MINUTOS_DIA) // 60:02d}:{minuto % 60:02d}"
    if modo == "un_dia":
        return {"hora": hora}
    return {"dia": DIAS[minuto // MINUTOS_DIA], "hora": hora}


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
    salarios_horas = 0.0
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
        peso = sum(inst.puntos[p - 1].peso_g for p in orden)
        vol = sum(inst.puntos[p - 1].volumen_l for p in orden)
        litros = km * v.consumo_litros_km
        combustible += litros * inst.precio_litro
        fijos += v.salario_fijo_cent / 100
        salarios_km += km * v.salario_por_km
        salida_v = solver.Value(m.salida[iv])
        fin_v = solver.Value(m.fin_ruta[iv])
        horas_cent = v.salario_cent_min * (fin_v - salida_v)
        salarios_horas += horas_cent / 100
        ruta = {
            "vehiculo": v.id,
            "paradas": [{
                "punto": inst.puntos[p - 1].id,
                "llegada": _momento(solver.Value(m.llegada[p - 1]), inst.modo),
                "fin_descarga": _momento(
                    solver.Value(m.llegada[p - 1]) + inst.puntos[p - 1].descarga_min,
                    inst.modo),
            } for p in orden],
            "km": round(km, 2), "litros": round(litros, 2),
            "peso_cargado_kg": round(peso / 1000, 2),
            "volumen_cargado_m3": round(vol / 1000, 2),
            "sale_de_base": _momento(salida_v, inst.modo),
            "costo": round(km * (v.consumo_litros_km * inst.precio_litro + v.salario_por_km)
                           + v.salario_fijo_cent / 100 + horas_cent / 100, 2),
        }
        if v.regresa_a_base:
            ruta["regresa_a_base"] = _momento(fin_v, inst.modo)
        rutas.append(ruta)
    objetivo = solver.ObjectiveValue()
    gap = 0.0 if status == cp_model.OPTIMAL or objetivo == 0 else round(
        abs(objetivo - solver.BestObjectiveBound()) / objetivo, 4)
    return {
        "estado": _estado(status),
        "gap_relativo": gap,
        "costo_total": round(objetivo / 100, 2),
        "desglose": {"combustible": round(combustible, 2), "salarios_fijos": round(fijos, 2),
                     "salarios_km": round(salarios_km, 2),
                     "salarios_horas": round(salarios_horas, 2)},
        "rutas": rutas,
        "vehiculos_sin_usar": sin_usar,
        "tiempo_solver_s": round(solver.WallTime(), 2),
        "fin_ultima_entrega": _momento(
            max(solver.Value(m.llegada[p]) + inst.puntos[p].descarga_min
                for p in range(len(inst.puntos))), inst.modo),
    }
