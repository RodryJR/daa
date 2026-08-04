from ortools.sat.python import cp_model


class Modelo:
    def __init__(self, inst):
        self.inst = inst
        self.model = cp_model.CpModel()
        self.x = {}
        self.visita = {}
        self.usado = []
        self.llegada = []
        self.salida = []
        self.fin_ruta = []
        self.tiempo_arco = {}
        self.costo_arco = {}
        self.costo_cent = 0
        self.makespan = None


def construir_modelo(inst):
    m = Modelo(inst)
    n = len(inst.puntos)
    nodos = range(n + 1)  # 0 = base, p = 1..n

    for iv, v in enumerate(inst.vehiculos):
        for i in nodos:
            for j in nodos:
                if i != j:
                    d = inst.dist_km[i][j]
                    m.tiempo_arco[iv, i, j] = round(d / v.velocidad_kmh * 60)
                    m.costo_arco[iv, i, j] = round(
                        d * (v.consumo_litros_km * inst.precio_litro + v.salario_por_km) * 100)

    for iv, v in enumerate(inst.vehiculos):
        arcos = []
        usado = m.model.NewBoolVar(f"usado_{v.id}")
        m.usado.append(usado)
        arcos.append((0, 0, usado.Not()))
        for p in range(1, n + 1):
            omitido = m.model.NewBoolVar(f"omite_{v.id}_{p}")
            arcos.append((p, p, omitido))
            m.visita[iv, p] = omitido.Not()
        for i in nodos:
            for j in nodos:
                if i != j:
                    lit = m.model.NewBoolVar(f"x_{v.id}_{i}_{j}")
                    m.x[iv, i, j] = lit
                    arcos.append((i, j, lit))
        m.model.AddCircuit(arcos)
        m.model.AddMaxEquality(usado, [m.visita[iv, p] for p in range(1, n + 1)])

    for p in range(1, n + 1):
        m.model.AddExactlyOne(m.visita[iv, p] for iv in range(len(inst.vehiculos)))

    costo = []
    for iv, v in enumerate(inst.vehiculos):
        for (jv, i, j), lit in m.x.items():
            if jv == iv:
                costo.append(m.costo_arco[iv, i, j] * lit)
    for iv, v in enumerate(inst.vehiculos):
        costo.append(v.salario_fijo_cent * m.usado[iv])
    m.costo_cent = sum(costo)
    return m
