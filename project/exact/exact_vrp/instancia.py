from dataclasses import dataclass

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
MINUTOS_DIA = 1440


class ErrorInstancia(ValueError):
    pass


def hora_a_minutos(hora):
    try:
        h, m = str(hora).split(":")
        h, m = int(h), int(m)
    except ValueError:
        raise ErrorInstancia(f"hora invalida: {hora!r} (formato esperado HH:MM)")
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ErrorInstancia(f"hora fuera de rango: {hora!r}")
    return h * 60 + m


def minuto_absoluto(dia, hora, modo, campo):
    if modo == "un_dia":
        if dia is not None:
            raise ErrorInstancia(f"{campo}: en modo un_dia no se indica 'dia'")
        return hora_a_minutos(hora)
    if dia not in DIAS:
        raise ErrorInstancia(f"{campo}: dia invalido o ausente: {dia!r}")
    return DIAS.index(dia) * MINUTOS_DIA + hora_a_minutos(hora)


@dataclass
class Vehiculo:
    id: str
    capacidad_peso_g: int
    capacidad_volumen_l: int
    consumo_litros_km: float
    velocidad_kmh: float
    salario_fijo_cent: int
    salario_por_km: float
    salario_cent_min: int
    regresa_a_base: bool
    turno_ini: int
    turno_fin: int


@dataclass
class Punto:
    id: str
    peso_g: int
    volumen_l: int
    descarga_min: int
    ventanas: list
    limite_min: int | None


@dataclass
class Instancia:
    modo: str
    horizonte_min: int
    dist_km: list
    precio_litro: float
    objetivo: str
    limite_solver_s: float
    vehiculos: list
    puntos: list


def _numero(valor, campo, minimo=0):
    if not isinstance(valor, (int, float)) or isinstance(valor, bool) or valor < minimo:
        raise ErrorInstancia(f"{campo} debe ser un numero >= {minimo}, no {valor!r}")
    return valor


def _rango(objeto, campo, modo, horizonte):
    ini = minuto_absoluto(objeto.get("dia"), objeto.get("desde"), modo, campo)
    fin = minuto_absoluto(objeto.get("dia"), objeto.get("hasta"), modo, campo)
    if ini > fin:
        raise ErrorInstancia(f"{campo}: ventana con desde > hasta")
    return ini, fin


def parsear_instancia(data):
    if not isinstance(data, dict):
        raise ErrorInstancia("la instancia debe ser un objeto JSON")
    modo = data.get("modo", "un_dia")
    if modo not in ("un_dia", "varios_dias"):
        raise ErrorInstancia(f"modo invalido: {modo!r} (use un_dia o varios_dias)")
    horizonte_dias = data.get("horizonte_dias", 7) if modo == "varios_dias" else 1
    if not isinstance(horizonte_dias, int) or not (1 <= horizonte_dias <= 7):
        raise ErrorInstancia("horizonte_dias debe ser un entero entre 1 y 7")
    horizonte = horizonte_dias * MINUTOS_DIA
    objetivo = data.get("objetivo", "costo")
    if objetivo not in ("costo", "tiempo", "costo_luego_tiempo"):
        raise ErrorInstancia(f"objetivo invalido: {objetivo!r}")
    precio = _numero(data.get("precio_combustible_litro", 0), "precio_combustible_litro")
    limite_s = _numero(data.get("limite_tiempo_solver_s", 60), "limite_tiempo_solver_s")

    crudos_v = data.get("vehiculos") or []
    if not isinstance(crudos_v, list):
        raise ErrorInstancia("vehiculos debe ser una lista")
    if not crudos_v:
        raise ErrorInstancia("se necesita al menos un vehiculo")
    vehiculos = []
    for cv in crudos_v:
        if not isinstance(cv, dict):
            raise ErrorInstancia("cada vehiculo debe ser un objeto")
        if "id" not in cv or cv.get("id") is None:
            raise ErrorInstancia("cada vehiculo necesita un id")
        turno = cv.get("turno")
        if turno is not None and not isinstance(turno, dict):
            raise ErrorInstancia(f"turno de {cv.get('id')} debe ser un objeto")
        t_ini, t_fin = (0, horizonte) if turno is None else _rango(turno, f"turno de {cv.get('id')}", modo, horizonte)
        vehiculos.append(Vehiculo(
            id=str(cv.get("id")),
            capacidad_peso_g=round(_numero(cv.get("capacidad_peso_kg"), "capacidad_peso_kg", 0.001) * 1000),
            capacidad_volumen_l=round(_numero(cv.get("capacidad_volumen_m3"), "capacidad_volumen_m3", 0.001) * 1000),
            consumo_litros_km=_numero(cv.get("consumo_litros_km", 0), "consumo_litros_km"),
            velocidad_kmh=_numero(cv.get("velocidad_kmh"), "velocidad_kmh", 0.001),
            salario_fijo_cent=round(_numero(cv.get("salario_fijo", 0), "salario_fijo") * 100),
            salario_por_km=_numero(cv.get("salario_por_km", 0), "salario_por_km"),
            salario_cent_min=round(_numero(cv.get("salario_por_hora", 0), "salario_por_hora") * 100 / 60),
            regresa_a_base=bool(cv.get("regresa_a_base", True)),
            turno_ini=t_ini, turno_fin=t_fin,
        ))
    ids_v = [v.id for v in vehiculos]
    if len(set(ids_v)) != len(ids_v):
        raise ErrorInstancia("hay ids de vehiculo repetidos")

    crudos_p = data.get("puntos") or []
    if not isinstance(crudos_p, list):
        raise ErrorInstancia("puntos debe ser una lista")
    if not crudos_p:
        raise ErrorInstancia("se necesita al menos un punto de entrega")
    puntos = []
    for cp in crudos_p:
        if not isinstance(cp, dict):
            raise ErrorInstancia("cada punto debe ser un objeto")
        if "id" not in cp or cp.get("id") is None:
            raise ErrorInstancia("cada punto necesita un id")
        productos = cp.get("productos") or []
        if not isinstance(productos, list):
            raise ErrorInstancia(f"productos de {cp.get('id')} debe ser una lista")
        if not productos:
            raise ErrorInstancia(f"el punto {cp.get('id')} no tiene productos")
        peso = sum(_numero(pr.get("peso_kg", 0), "peso_kg") for pr in productos)
        vol = sum(_numero(pr.get("volumen_m3", 0), "volumen_m3") for pr in productos)
        ventanas_raw = cp.get("ventanas") or []
        if not isinstance(ventanas_raw, list):
            raise ErrorInstancia(f"ventanas de {cp.get('id')} debe ser una lista")
        ventanas = [_rango(v, f"ventana de {cp.get('id')}", modo, horizonte)
                    for v in ventanas_raw]
        lim = cp.get("fecha_limite")
        if lim is not None and not isinstance(lim, dict):
            raise ErrorInstancia(f"fecha_limite de {cp.get('id')} debe ser un objeto")
        limite = None if lim is None else minuto_absoluto(
            lim.get("dia"), lim.get("hora"), modo, f"fecha_limite de {cp.get('id')}")
        puntos.append(Punto(
            id=str(cp.get("id")),
            peso_g=round(peso * 1000), volumen_l=round(vol * 1000),
            descarga_min=round(_numero(cp.get("tiempo_descarga_min", 0), "tiempo_descarga_min")),
            ventanas=sorted(ventanas), limite_min=limite,
        ))
    ids_p = [p.id for p in puntos]
    if len(set(ids_p + ids_v)) != len(ids_p) + len(ids_v):
        raise ErrorInstancia("hay ids de punto repetidos o iguales a un vehiculo")

    matriz = data.get("matriz_distancias_km")
    n = len(puntos) + 1
    if (not isinstance(matriz, list) or len(matriz) != n
            or any(not isinstance(f, list) or len(f) != n for f in matriz)):
        raise ErrorInstancia(f"matriz_distancias_km debe ser cuadrada de {n}x{n} (base + puntos)")
    for i, fila in enumerate(matriz):
        for j, d in enumerate(fila):
            _numero(d, f"matriz[{i}][{j}]")
        if fila[i] != 0:
            raise ErrorInstancia(f"matriz: la diagonal debe ser 0 (fila {i})")

    return Instancia(modo=modo, horizonte_min=horizonte, dist_km=matriz,
                     precio_litro=precio, objetivo=objetivo, limite_solver_s=limite_s,
                     vehiculos=vehiculos, puntos=puntos)
