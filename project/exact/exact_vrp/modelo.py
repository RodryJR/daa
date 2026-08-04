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

    for iv, v in enumerate(inst.vehiculos):
        m.model.Add(sum(inst.puntos[p - 1].peso_g * m.visita[iv, p]
                        for p in range(1, n + 1)) <= v.capacidad_peso_g)
        m.model.Add(sum(inst.puntos[p - 1].volumen_l * m.visita[iv, p]
                        for p in range(1, n + 1)) <= v.capacidad_volumen_l)

    costo = []
    for iv, v in enumerate(inst.vehiculos):
        for (jv, i, j), lit in m.x.items():
            if jv == iv:
                costo.append(m.costo_arco[iv, i, j] * lit)
    for iv, v in enumerate(inst.vehiculos):
        costo.append(v.salario_fijo_cent * m.usado[iv])

    H = inst.horizonte_min
    # la ventana acota el INICIO de la descarga: una descarga puede terminar
    # despues de H, asi que makespan necesita margen o podaria llegadas
    # legitimas al final del horizonte
    margen = max((p.descarga_min for p in inst.puntos), default=0)
    m.makespan = m.model.NewIntVar(0, H + margen, "makespan")
    for p in range(1, n + 1):
        pt = inst.puntos[p - 1]
        tope = H - 1 if pt.limite_min is None else min(H - 1, pt.limite_min)
        llegada = m.model.NewIntVar(0, tope, f"llegada_{pt.id}")
        m.llegada.append(llegada)
        if pt.ventanas:
            elegida = [m.model.NewBoolVar(f"vent_{pt.id}_{k}")
                       for k in range(len(pt.ventanas))]
            m.model.AddExactlyOne(elegida)
            for k, (ini, fin) in enumerate(pt.ventanas):
                m.model.Add(llegada >= ini).OnlyEnforceIf(elegida[k])
                m.model.Add(llegada <= fin).OnlyEnforceIf(elegida[k])
        m.model.Add(m.makespan >= llegada + pt.descarga_min)

    for iv, v in enumerate(inst.vehiculos):
        # mismo problema que el makespan: si no se declaro turno, turno_fin
        # cae exactamente en H (parsear_instancia), y el cierre de ruta
        # (descarga + regreso) puede terminar despues de H aunque la llegada
        # sea legitima. A diferencia del makespan, aqui el margen tambien
        # debe cubrir el tramo de regreso a base, no solo la descarga. Un
        # turno EXPLICITO si es un limite duro (nunca es numericamente igual
        # a H: un HH:MM valido topa en 23:59) y no se relaja.
        max_regreso = (max((m.tiempo_arco[iv, i, 0] for i in range(1, n + 1)), default=0)
                       if v.regresa_a_base else 0)
        fin_tope = v.turno_fin + margen + max_regreso if v.turno_fin == H else v.turno_fin
        salida = m.model.NewIntVar(v.turno_ini, v.turno_fin, f"salida_{v.id}")
        fin = m.model.NewIntVar(v.turno_ini, fin_tope, f"fin_{v.id}")
        m.salida.append(salida)
        m.fin_ruta.append(fin)
        m.model.Add(fin == salida).OnlyEnforceIf(m.usado[iv].Not())
        for j in range(1, n + 1):
            m.model.Add(m.llegada[j - 1] >= salida + m.tiempo_arco[iv, 0, j]
                        ).OnlyEnforceIf(m.x[iv, 0, j])
        for i in range(1, n + 1):
            desc = inst.puntos[i - 1].descarga_min
            for j in range(1, n + 1):
                if i != j:
                    m.model.Add(m.llegada[j - 1] >= m.llegada[i - 1] + desc
                                + m.tiempo_arco[iv, i, j]).OnlyEnforceIf(m.x[iv, i, j])
            regreso = m.tiempo_arco[iv, i, 0] if v.regresa_a_base else 0
            m.model.Add(fin >= m.llegada[i - 1] + desc + regreso
                        ).OnlyEnforceIf(m.x[iv, i, 0])
        costo.append(v.salario_cent_min * (fin - salida))
    m.costo_cent = sum(costo)
    return m
