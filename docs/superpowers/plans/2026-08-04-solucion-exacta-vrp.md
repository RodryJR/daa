# Solver exacto VRP (CP-SAT) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Módulo Python `exact_vrp` que resuelve exactamente el ruteo de una flota heterogénea (peso+volumen, consumo, salarios configurables, ventanas semanales, rutas abiertas), embebible vía `resolver(dict) -> dict`.

**Architecture:** Pipeline puro: `parsear_instancia` (validación → dataclasses en unidades enteras) → `diagnosticar` (pre-chequeos con mensajes accionables) → `construir_modelo` (CP-SAT: un AddCircuit por vehículo, llegadas en minutos, objetivo en centavos) → `resolver` (orquesta, incluye lexicográfico en dos fases) → dict de salida JSON-friendly. Spec: `docs/superpowers/specs/2026-08-04-solucion-exacta-vrp-design.md`.

**Tech Stack:** Python 3.14 (venv en `project/exact/.venv`), ortools>=9.15 (CP-SAT), pytest.

## Global Constraints

- Todo en español: campos JSON, mensajes de error, nombres públicos.
- Unidades internas enteras: minutos, centavos, gramos, litros (m³×1000). Distancias quedan float km en `Instancia`; se redondean POR ARCO al construir el modelo: `tiempo = round(km/velocidad*60)`, `costo = round(km*(consumo*precio + salario_por_km)*100)`.
- Días: `lunes`=0 .. `domingo`=6; horizonte arranca lunes 00:00; `un_dia` = 1440 min.
- Ventanas inclusivas: llegada (inicio de descarga) ∈ [desde, hasta]. La espera está permitida.
- La librería no hace I/O (solo `run.py`).
- Defaults del spec: `salario_*`=0, `regresa_a_base`=true, `turno`=todo el horizonte, `tiempo_descarga_min`=0, `ventanas`=[] (sin restricción), `objetivo`="costo", `limite_tiempo_solver_s`=60, `horizonte_dias`=7, `precio_combustible_litro`=0.
- Tests corren con `cd /home/dario/daa/project/exact && .venv/bin/python -m pytest tests/ -v`.
- TDD estricto (test en rojo antes de cada implementación) y un commit por tarea.

---

### Task 1: Esqueleto, venv y dependencias

**Files:**
- Create: `project/exact/exact_vrp/__init__.py`, `project/exact/requirements.txt`, `project/exact/tests/test_setup.py`
- Modify: `.gitignore` (raíz)

**Interfaces:**
- Produces: paquete `exact_vrp` importable; venv `.venv` con ortools y pytest.

- [ ] **Step 1: Crear estructura y venv**

```bash
mkdir -p /home/dario/daa/project/exact/exact_vrp /home/dario/daa/project/exact/tests
cd /home/dario/daa/project/exact
python3 -m venv .venv
.venv/bin/pip install --quiet "ortools>=9.15" "pytest>=8"
printf 'ortools>=9.15\npytest>=8\n' > requirements.txt
```

Si la instalación de ortools falla por falta de wheel para Python 3.14, detenerse y reportarlo (plan B del spec: instalar python 3.13 y recrear el venv con él).

- [ ] **Step 2: Test de humo del entorno**

`project/exact/tests/test_setup.py`:
```python
def test_ortools_disponible():
    from ortools.sat.python import cp_model
    assert hasattr(cp_model, "CpModel")

def test_paquete_importable():
    import exact_vrp
    assert exact_vrp is not None
```

`project/exact/exact_vrp/__init__.py`:
```python
```
(vacío por ahora; `resolver` se exporta en la Task 4)

- [ ] **Step 3: Ejecutar tests**

Run: `cd /home/dario/daa/project/exact && .venv/bin/python -m pytest tests/ -v`
Expected: 2 PASS

- [ ] **Step 4: Ignorar el venv y commitear**

Añadir a `/home/dario/daa/.gitignore` la línea `.venv/`, luego:
```bash
cd /home/dario/daa && git add .gitignore project/exact && git commit -m "exact: esqueleto del paquete y venv con ortools"
```

---

### Task 2: `instancia.py` — parseo y validación

**Files:**
- Create: `project/exact/exact_vrp/instancia.py`, `project/exact/tests/util.py`, `project/exact/tests/test_instancia.py`

**Interfaces:**
- Produces:
  - `DIAS: list[str]`, `MINUTOS_DIA = 1440`, `class ErrorInstancia(ValueError)`
  - `hora_a_minutos(hora: str) -> int`
  - `minuto_absoluto(dia: str|None, hora: str, modo: str, campo: str) -> int`
  - `@dataclass Vehiculo(id, capacidad_peso_g: int, capacidad_volumen_l: int, consumo_litros_km: float, velocidad_kmh: float, salario_fijo_cent: int, salario_por_km: float, salario_cent_min: int, regresa_a_base: bool, turno_ini: int, turno_fin: int)`
  - `@dataclass Punto(id, peso_g: int, volumen_l: int, descarga_min: int, ventanas: list[tuple[int,int]], limite_min: int|None)`
  - `@dataclass Instancia(modo, horizonte_min: int, dist_km: list[list[float]], precio_litro: float, objetivo: str, limite_solver_s: float, vehiculos: list[Vehiculo], puntos: list[Punto])`
  - `parsear_instancia(data: dict) -> Instancia` (lanza `ErrorInstancia` con mensaje en español)
  - Tests: `tests/util.py` con `vehiculo(**kw)`, `punto(**kw)`, `instancia_minima(**kw)`.

- [ ] **Step 1: Escribir tests en rojo**

`project/exact/tests/util.py`:
```python
def vehiculo(**kw):
    base = {"id": "v1", "capacidad_peso_kg": 1000, "capacidad_volumen_m3": 10,
            "consumo_litros_km": 0.1, "velocidad_kmh": 60}
    base.update(kw)
    return base

def punto(**kw):
    base = {"id": "p1", "productos": [{"peso_kg": 10, "volumen_m3": 0.1}]}
    base.update(kw)
    return base

def instancia_minima(**kw):
    base = {
        "modo": "un_dia",
        "matriz_distancias_km": [[0, 10], [10, 0]],
        "precio_combustible_litro": 1.0,
        "vehiculos": [vehiculo()],
        "puntos": [punto()],
    }
    base.update(kw)
    return base
```

`project/exact/tests/test_instancia.py`:
```python
import pytest
from exact_vrp.instancia import (ErrorInstancia, parsear_instancia,
                                 hora_a_minutos, minuto_absoluto)
from util import instancia_minima, vehiculo, punto


def test_hora_a_minutos():
    assert hora_a_minutos("08:30") == 510
    with pytest.raises(ErrorInstancia):
        hora_a_minutos("25:00")
    with pytest.raises(ErrorInstancia):
        hora_a_minutos("0830")

def test_minuto_absoluto_varios_dias():
    assert minuto_absoluto("martes", "09:00", "varios_dias", "x") == 1440 + 540

def test_minuto_absoluto_un_dia_rechaza_dia():
    with pytest.raises(ErrorInstancia):
        minuto_absoluto("martes", "09:00", "un_dia", "x")

def test_parsea_minima_con_defaults():
    inst = parsear_instancia(instancia_minima())
    assert inst.horizonte_min == 1440
    assert inst.objetivo == "costo"
    v = inst.vehiculos[0]
    assert (v.salario_fijo_cent, v.salario_por_km, v.salario_cent_min) == (0, 0.0, 0)
    assert v.regresa_a_base is True
    assert (v.turno_ini, v.turno_fin) == (0, 1440)
    p = inst.puntos[0]
    assert (p.peso_g, p.volumen_l) == (10000, 100)
    assert p.ventanas == [] and p.limite_min is None and p.descarga_min == 0

def test_convierte_unidades_y_ventanas():
    data = instancia_minima(modo="varios_dias", horizonte_dias=7)
    data["vehiculos"][0]["salario_fijo"] = 12.5
    data["vehiculos"][0]["salario_por_hora"] = 60
    data["puntos"][0]["ventanas"] = [{"dia": "martes", "desde": "09:00", "hasta": "13:00"}]
    data["puntos"][0]["fecha_limite"] = {"dia": "miercoles", "hora": "18:00"}
    inst = parsear_instancia(data)
    assert inst.vehiculos[0].salario_fijo_cent == 1250
    assert inst.vehiculos[0].salario_cent_min == 100
    assert inst.puntos[0].ventanas == [(1440 + 540, 1440 + 780)]
    assert inst.puntos[0].limite_min == 2 * 1440 + 1080

@pytest.mark.parametrize("romper,mensaje", [
    (lambda d: d.update(modo="mensual"), "modo"),
    (lambda d: d.update(matriz_distancias_km=[[0, 1], [1, 0], [0, 0]]), "matriz"),
    (lambda d: d.update(matriz_distancias_km=[[0, -1], [1, 0]]), "matriz"),
    (lambda d: d.update(matriz_distancias_km=[[5, 1], [1, 0]]), "diagonal"),
    (lambda d: d.update(vehiculos=[]), "vehiculo"),
    (lambda d: d.update(puntos=[]), "punto"),
    (lambda d: d["puntos"][0].update(productos=[]), "producto"),
    (lambda d: d["vehiculos"][0].update(velocidad_kmh=0), "velocidad"),
    (lambda d: d["vehiculos"][0].update(id="p1x") or d["vehiculos"].append(dict(d["vehiculos"][0])), "repetido"),
    (lambda d: d["puntos"][0].update(ventanas=[{"desde": "10:00", "hasta": "09:00"}]), "ventana"),
])
def test_validaciones(romper, mensaje):
    data = instancia_minima()
    romper(data)
    with pytest.raises(ErrorInstancia) as e:
        parsear_instancia(data)
    assert mensaje in str(e.value).lower()
```

- [ ] **Step 2: Verificar rojo**

Run: `.venv/bin/python -m pytest tests/test_instancia.py -v`
Expected: FAIL/ERROR con `ModuleNotFoundError: exact_vrp.instancia`

- [ ] **Step 3: Implementar `instancia.py`**

```python
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
    if not crudos_v:
        raise ErrorInstancia("se necesita al menos un vehiculo")
    vehiculos = []
    for cv in crudos_v:
        turno = cv.get("turno")
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
    if not crudos_p:
        raise ErrorInstancia("se necesita al menos un punto de entrega")
    puntos = []
    for cp in crudos_p:
        productos = cp.get("productos") or []
        if not productos:
            raise ErrorInstancia(f"el punto {cp.get('id')} no tiene productos")
        peso = sum(_numero(pr.get("peso_kg", 0), "peso_kg") for pr in productos)
        vol = sum(_numero(pr.get("volumen_m3", 0), "volumen_m3") for pr in productos)
        ventanas = [_rango(v, f"ventana de {cp.get('id')}", modo, horizonte)
                    for v in (cp.get("ventanas") or [])]
        lim = cp.get("fecha_limite")
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
```

- [ ] **Step 4: Verificar verde**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: todos PASS

- [ ] **Step 5: Commit**

```bash
cd /home/dario/daa && git add project/exact && git commit -m "exact: parseo y validacion de instancias"
```

---

### Task 3: `diagnostico.py` — pre-chequeos de factibilidad

**Files:**
- Create: `project/exact/exact_vrp/diagnostico.py`, `project/exact/tests/test_diagnostico.py`

**Interfaces:**
- Consumes: `Instancia`, `Vehiculo`, `Punto` de `exact_vrp.instancia`.
- Produces: `diagnosticar(instancia) -> list[str]` (vacía si pasa todo; cada string incluye los ids implicados).

- [ ] **Step 1: Tests en rojo**

`project/exact/tests/test_diagnostico.py`:
```python
from exact_vrp.instancia import parsear_instancia
from exact_vrp.diagnostico import diagnosticar
from util import instancia_minima, vehiculo, punto


def _diag(data):
    return diagnosticar(parsear_instancia(data))

def test_instancia_sana_sin_errores():
    assert _diag(instancia_minima()) == []

def test_punto_que_no_cabe_en_ningun_vehiculo():
    # dos vehiculos de 1000 kg: el punto de 1500 kg no cabe en ninguno por
    # separado, pero la flota agregada (2000 kg) si alcanza, aislando el
    # chequeo 1 del chequeo 2.
    data = instancia_minima(vehiculos=[vehiculo(id="v1"), vehiculo(id="v2")])
    data["puntos"][0]["productos"] = [{"peso_kg": 1500, "volumen_m3": 0.1}]
    errores = _diag(data)
    assert len(errores) == 1 and "p1" in errores[0] and "no cabe" in errores[0]

def test_demanda_total_excede_flota():
    data = instancia_minima(
        matriz_distancias_km=[[0, 1, 1], [1, 0, 1], [1, 1, 0]],
        puntos=[punto(id="p1", productos=[{"peso_kg": 800, "volumen_m3": 1}]),
                punto(id="p2", productos=[{"peso_kg": 800, "volumen_m3": 1}])])
    assert any("excede" in e for e in _diag(data))

def test_limite_anterior_a_ventanas():
    data = instancia_minima()
    data["puntos"][0]["ventanas"] = [{"desde": "10:00", "hasta": "12:00"}]
    data["puntos"][0]["fecha_limite"] = {"hora": "09:00"}
    assert any("fecha_limite" in e and "p1" in e for e in _diag(data))

def test_ventana_fuera_del_horizonte():
    data = instancia_minima(modo="varios_dias", horizonte_dias=2)
    data["puntos"][0]["ventanas"] = [{"dia": "viernes", "desde": "09:00", "hasta": "10:00"}]
    assert any("horizonte" in e for e in _diag(data))

def test_punto_inalcanzable_en_sus_ventanas():
    data = instancia_minima(matriz_distancias_km=[[0, 300], [300, 0]])
    data["puntos"][0]["ventanas"] = [{"desde": "00:00", "hasta": "01:00"}]
    assert any("alcanza" in e for e in _diag(data))
```

- [ ] **Step 2: Verificar rojo**

Run: `.venv/bin/python -m pytest tests/test_diagnostico.py -v`
Expected: FAIL con `ModuleNotFoundError: exact_vrp.diagnostico`

- [ ] **Step 3: Implementar**

```python
def diagnosticar(inst):
    '''
    Pre-chequeos de factibilidad. Devuelve mensajes accionables; lista vacia
    si la instancia pasa todos.
    '''
    errores = []

    for p in inst.puntos:
        if all(p.peso_g > v.capacidad_peso_g or p.volumen_l > v.capacidad_volumen_l
               for v in inst.vehiculos):
            errores.append(
                f"el punto {p.id} ({p.peso_g/1000} kg, {p.volumen_l/1000} m3) "
                f"no cabe en ningun vehiculo")

    peso_total = sum(p.peso_g for p in inst.puntos)
    vol_total = sum(p.volumen_l for p in inst.puntos)
    peso_flota = sum(v.capacidad_peso_g for v in inst.vehiculos)
    vol_flota = sum(v.capacidad_volumen_l for v in inst.vehiculos)
    if peso_total > peso_flota or vol_total > vol_flota:
        errores.append(
            f"la demanda total ({peso_total/1000:g} kg, {vol_total/1000:g} m3) "
            f"excede la capacidad agregada de la flota "
            f"({peso_flota/1000:g} kg, {vol_flota/1000:g} m3)")

    for p in inst.puntos:
        for ini, fin in p.ventanas:
            if fin >= inst.horizonte_min:
                errores.append(f"el punto {p.id} tiene una ventana fuera del horizonte")
                break
        if p.ventanas and p.limite_min is not None and p.limite_min < min(v[0] for v in p.ventanas):
            errores.append(
                f"la fecha_limite del punto {p.id} es anterior a todas sus ventanas")

    for idx, p in enumerate(inst.puntos, start=1):
        llegada_min = min(v.turno_ini + round(inst.dist_km[0][idx] / v.velocidad_kmh * 60)
                          for v in inst.vehiculos)
        tope = p.limite_min if p.limite_min is not None else inst.horizonte_min - 1
        if p.ventanas:
            tope = min(tope, max(fin for _, fin in p.ventanas))
        if llegada_min > tope:
            errores.append(
                f"ningun vehiculo alcanza el punto {p.id} a tiempo "
                f"(llegada minima posible: minuto {llegada_min})")

    return errores
```

- [ ] **Step 4: Verificar verde**

Run: `.venv/bin/python -m pytest tests/ -v` — Expected: todos PASS

- [ ] **Step 5: Commit**

```bash
cd /home/dario/daa && git add project/exact && git commit -m "exact: pre-chequeos de factibilidad"
```

---

### Task 4: Núcleo de `modelo.py` + `solver.py` — ruteo y combustible

**Files:**
- Create: `project/exact/exact_vrp/modelo.py`, `project/exact/exact_vrp/solver.py`, `project/exact/tests/test_solver_nucleo.py`
- Modify: `project/exact/exact_vrp/__init__.py`

**Interfaces:**
- Consumes: `Instancia` y `diagnosticar`.
- Produces:
  - `modelo.construir_modelo(inst) -> Modelo` con atributos: `model` (CpModel), `x` (dict `(iv,i,j) -> BoolVar`, nodos 0=base, p=1..n), `visita` (dict `(iv,p) -> BoolVar`), `usado` (list BoolVar por vehículo), `llegada` (list IntVar por punto, índice 0..n-1), `salida`/`fin_ruta` (list IntVar por vehículo), `costo_cent` (expresión lineal), `makespan` (IntVar), `tiempo_arco` y `costo_arco` (dicts `(iv,i,j) -> int`).
  - `solver.resolver(data: dict) -> dict` — API pública (exportada en `__init__.py`).
  - Salida mínima de esta task: `estado`, `costo_total`, `gap_relativo`, `desglose` (solo `combustible`; resto 0), `rutas` (con `vehiculo`, `paradas` [solo `punto`], `km`, `litros`, `costo`), `vehiculos_sin_usar`, `tiempo_solver_s`.

- [ ] **Step 1: Test en rojo** — óptimo verificable a mano: 3 puntos en línea (x=10,20,30), ruta cerrada 0→1→2→3→0 = 60 km, consumo 0.1 × precio 1.0 → 6.00.

`project/exact/tests/test_solver_nucleo.py`:
```python
from exact_vrp import resolver
from util import instancia_minima, vehiculo, punto

# d(a,c)=25 (no 20) rompe el empate estructural de puntos colineales: solo
# los ordenes a,b,c y c,b,a cuestan 60 km
LINEA = [[0, 10, 20, 30], [10, 0, 10, 25], [20, 10, 0, 10], [30, 25, 10, 0]]

def test_tsp_en_linea_optimo():
    data = instancia_minima(
        matriz_distancias_km=LINEA,
        vehiculos=[vehiculo()],
        puntos=[punto(id="a"), punto(id="b"), punto(id="c")])
    sol = resolver(data)
    assert sol["estado"] == "OPTIMO"
    assert sol["costo_total"] == 6.0
    assert sol["desglose"]["combustible"] == 6.0
    ruta = sol["rutas"][0]
    orden = [par["punto"] for par in ruta["paradas"]]
    assert orden in (["a", "b", "c"], ["c", "b", "a"])
    assert ruta["km"] == 60.0 and ruta["litros"] == 6.0
    assert sol["vehiculos_sin_usar"] == []

def test_infactible_por_diagnostico():
    data = instancia_minima()
    data["puntos"][0]["productos"] = [{"peso_kg": 5000, "volumen_m3": 0.1}]
    sol = resolver(data)
    assert sol["estado"] == "INFACTIBLE" and "no cabe" in sol["motivo"]
```

- [ ] **Step 2: Verificar rojo**

Run: `.venv/bin/python -m pytest tests/test_solver_nucleo.py -v`
Expected: FAIL con ImportError de `resolver`

- [ ] **Step 3: Implementar núcleo**

`project/exact/exact_vrp/modelo.py`:
```python
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
        # sin esto, un vehiculo "no usado" podria formar un sub-circuito
        # huerfano entre puntos sin pasar por la base
        m.model.AddMaxEquality(usado, [m.visita[iv, p] for p in range(1, n + 1)])
        for i in nodos:
            for j in nodos:
                if i != j:
                    lit = m.model.NewBoolVar(f"x_{v.id}_{i}_{j}")
                    m.x[iv, i, j] = lit
                    arcos.append((i, j, lit))
        m.model.AddCircuit(arcos)

    for p in range(1, n + 1):
        m.model.AddExactlyOne(m.visita[iv, p] for iv in range(len(inst.vehiculos)))

    costo = []
    for iv, v in enumerate(inst.vehiculos):
        for (jv, i, j), lit in m.x.items():
            if jv == iv:
                costo.append(m.costo_arco[iv, i, j] * lit)
    m.costo_cent = sum(costo)
    return m
```

`project/exact/exact_vrp/solver.py`:
```python
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
        rutas.append({
            "vehiculo": v.id,
            "paradas": [{"punto": inst.puntos[p - 1].id} for p in orden],
            "km": round(km, 2), "litros": round(litros, 2),
            "costo": round(km * (v.consumo_litros_km * inst.precio_litro
                                 + v.salario_por_km), 2),
        })
    objetivo = solver.ObjectiveValue()
    gap = 0.0 if status == cp_model.OPTIMAL or objetivo == 0 else round(
        abs(objetivo - solver.BestObjectiveBound()) / objetivo, 4)
    return {
        "estado": _estado(status),
        "gap_relativo": gap,
        "costo_total": round(objetivo / 100, 2),
        "desglose": {"combustible": round(combustible, 2), "salarios_fijos": 0.0,
                     "salarios_km": 0.0, "salarios_horas": 0.0},
        "rutas": rutas,
        "vehiculos_sin_usar": sin_usar,
        "tiempo_solver_s": round(solver.WallTime(), 2),
    }
```

`project/exact/exact_vrp/__init__.py`:
```python
from exact_vrp.solver import resolver

__all__ = ["resolver"]
```

- [ ] **Step 4: Verificar verde**

Run: `.venv/bin/python -m pytest tests/ -v` — Expected: todos PASS

- [ ] **Step 5: Commit**

```bash
cd /home/dario/daa && git add project/exact && git commit -m "exact: nucleo CP-SAT (circuitos, combustible, extraccion de rutas)"
```

---

### Task 5: Selección de flota — salario fijo y desglose

**Files:**
- Modify: `project/exact/exact_vrp/modelo.py` (sumar fijos al costo), `project/exact/exact_vrp/solver.py` (desglose)
- Create: `project/exact/tests/test_flota.py`

**Interfaces:**
- Consumes: todo lo de Task 4.
- Produces: `costo_cent` incluye `v.salario_fijo_cent * usado[iv]`; desglose reporta `salarios_fijos` y `salarios_km` reales; `costo` de cada ruta incluye el fijo.

- [ ] **Step 1: Tests en rojo**

`project/exact/tests/test_flota.py`:
```python
from exact_vrp import resolver
from util import instancia_minima, vehiculo, punto

TRES = [[0, 10, 20], [10, 0, 10], [20, 10, 0]]

def test_fijo_alto_junta_los_puntos_en_un_camion():
    data = instancia_minima(
        matriz_distancias_km=TRES,
        vehiculos=[vehiculo(id="v1", salario_fijo=5), vehiculo(id="v2", salario_fijo=5)],
        puntos=[punto(id="a"), punto(id="b")])
    sol = resolver(data)
    # 1 camion: 40 km * 0.1 = 4.0 + 5 fijo = 9.0; 2 camiones: 6.0 + 10 = 16.0
    assert sol["costo_total"] == 9.0
    assert len(sol["rutas"]) == 1 and len(sol["vehiculos_sin_usar"]) == 1
    assert sol["desglose"]["salarios_fijos"] == 5.0

def test_elige_el_camion_de_menor_consumo():
    data = instancia_minima(
        vehiculos=[vehiculo(id="tragon", consumo_litros_km=0.3),
                   vehiculo(id="eficiente", consumo_litros_km=0.1)])
    sol = resolver(data)
    assert sol["rutas"][0]["vehiculo"] == "eficiente"

def test_salario_por_km_en_desglose():
    data = instancia_minima(vehiculos=[vehiculo(salario_por_km=0.5)])
    sol = resolver(data)  # 20 km: combustible 2.0, salario_km 10.0
    assert sol["desglose"]["salarios_km"] == 10.0
    assert sol["costo_total"] == 12.0
```

- [ ] **Step 2: Verificar rojo**

Run: `.venv/bin/python -m pytest tests/test_flota.py -v`
Expected: FAIL (costo_total sin fijo; salarios_km en 0)

- [ ] **Step 3: Implementar**

En `construir_modelo`, tras armar `costo`:
```python
    for iv, v in enumerate(inst.vehiculos):
        costo.append(v.salario_fijo_cent * m.usado[iv])
```

En `_extraer`: acumular `fijos += v.salario_fijo_cent / 100` y
`salarios_km += km * v.salario_por_km` por vehículo usado; sumar el fijo al
`costo` de la ruta; poner ambos en el desglose:
```python
        rutas.append({
            "vehiculo": v.id,
            "paradas": [{"punto": inst.puntos[p - 1].id} for p in orden],
            "km": round(km, 2), "litros": round(litros, 2),
            "costo": round(km * (v.consumo_litros_km * inst.precio_litro + v.salario_por_km)
                           + v.salario_fijo_cent / 100, 2),
        })
```

- [ ] **Step 4: Verificar verde** — `.venv/bin/python -m pytest tests/ -v`

- [ ] **Step 5: Commit** — `git add project/exact && git commit -m "exact: salario fijo por camion usado y desglose"`

---

### Task 6: Capacidades 2D (peso y volumen)

**Files:**
- Modify: `project/exact/exact_vrp/modelo.py`
- Create: `project/exact/tests/test_capacidades.py`

**Interfaces:**
- Produces: restricciones `Σ peso_g·visita ≤ capacidad_peso_g` y `Σ volumen_l·visita ≤ capacidad_volumen_l` por vehículo; salida de ruta gana `peso_cargado_kg` y `volumen_cargado_m3`.

- [ ] **Step 1: Tests en rojo**

`project/exact/tests/test_capacidades.py`:
```python
from exact_vrp import resolver
from util import instancia_minima, vehiculo, punto

TRES = [[0, 10, 20], [10, 0, 10], [20, 10, 0]]

def _dos_puntos(**producto):
    return [punto(id="a", productos=[dict(producto)]),
            punto(id="b", productos=[dict(producto)])]

def test_peso_obliga_a_dos_camiones():
    data = instancia_minima(
        matriz_distancias_km=TRES,
        vehiculos=[vehiculo(id="v1", capacidad_peso_kg=100),
                   vehiculo(id="v2", capacidad_peso_kg=100)],
        puntos=_dos_puntos(peso_kg=60, volumen_m3=0.1))
    sol = resolver(data)
    assert len(sol["rutas"]) == 2
    assert sol["rutas"][0]["peso_cargado_kg"] == 60.0

def test_volumen_obliga_a_dos_camiones():
    data = instancia_minima(
        matriz_distancias_km=TRES,
        vehiculos=[vehiculo(id="v1", capacidad_volumen_m3=1),
                   vehiculo(id="v2", capacidad_volumen_m3=1)],
        puntos=_dos_puntos(peso_kg=1, volumen_m3=0.6))
    sol = resolver(data)
    assert len(sol["rutas"]) == 2

def test_caben_juntos_si_hay_capacidad():
    data = instancia_minima(matriz_distancias_km=TRES,
                            vehiculos=[vehiculo(), vehiculo(id="v2")],
                            puntos=_dos_puntos(peso_kg=60, volumen_m3=0.6))
    assert len(resolver(data)["rutas"]) == 1
```

- [ ] **Step 2: Verificar rojo** — el primero y el segundo FALLAN (hoy los junta).

- [ ] **Step 3: Implementar** — en `construir_modelo`, tras `AddExactlyOne`:

```python
    for iv, v in enumerate(inst.vehiculos):
        m.model.Add(sum(inst.puntos[p - 1].peso_g * m.visita[iv, p]
                        for p in range(1, n + 1)) <= v.capacidad_peso_g)
        m.model.Add(sum(inst.puntos[p - 1].volumen_l * m.visita[iv, p]
                        for p in range(1, n + 1)) <= v.capacidad_volumen_l)
```

En `_extraer`, dentro del armado de la ruta:
```python
        peso = sum(inst.puntos[p - 1].peso_g for p in orden)
        vol = sum(inst.puntos[p - 1].volumen_l for p in orden)
        # ... y en el dict de la ruta:
            "peso_cargado_kg": round(peso / 1000, 2),
            "volumen_cargado_m3": round(vol / 1000, 2),
```

- [ ] **Step 4: Verificar verde** — `.venv/bin/python -m pytest tests/ -v`

- [ ] **Step 5: Commit** — `git commit -m "exact: capacidades de peso y volumen"`

---

### Task 7: Tiempos, ventanas (un_dia), descarga, turno y salario por hora

**Files:**
- Modify: `project/exact/exact_vrp/modelo.py`, `project/exact/exact_vrp/solver.py`
- Create: `project/exact/tests/test_tiempos.py`

**Interfaces:**
- Produces: `llegada[p-1]` (IntVar por punto), `salida[iv]`, `fin_ruta[iv]`, `makespan`; costo suma `salario_cent_min·(fin_ruta−salida)`; salida JSON gana `llegada`/`fin_descarga` por parada, `sale_de_base`/`regresa_a_base` por ruta, `desglose.salarios_horas`, `fin_ultima_entrega`; helper `_momento(minuto, modo) -> dict` (`{"hora": "HH:MM"}` o `{"dia": ..., "hora": ...}`).

- [ ] **Step 1: Tests en rojo**

`project/exact/tests/test_tiempos.py`:
```python
from exact_vrp import resolver
from util import instancia_minima, vehiculo, punto

# base, A en x=30, B en x=60; vel 60 km/h => 0-A 30', A-B 30', 0-B 60'
DOS = [[0, 30, 60], [30, 0, 30], [60, 30, 0]]

def _data(**kw):
    base = instancia_minima(
        matriz_distancias_km=DOS,
        vehiculos=[vehiculo()],
        puntos=[punto(id="a"), punto(id="b")])
    base.update(kw)
    return base

def test_ventana_invierte_el_orden():
    # sin salario por hora la llegada exacta no esta fijada por el optimo:
    # solo se asegura el orden (la hora se fija en el test del salario).
    data = _data()
    data["puntos"][0]["ventanas"] = [{"desde": "10:00", "hasta": "10:30"}]
    data["puntos"][1]["ventanas"] = [{"desde": "08:00", "hasta": "09:00"}]
    sol = resolver(data)
    orden = [p["punto"] for p in sol["rutas"][0]["paradas"]]
    assert orden == ["b", "a"]

def test_salario_por_hora_cuenta_la_duracion():
    data = _data(vehiculos=[vehiculo(salario_por_hora=60)])
    data["puntos"][0]["ventanas"] = [{"desde": "10:00", "hasta": "10:30"}]
    data["puntos"][1]["ventanas"] = [{"desde": "08:00", "hasta": "09:00"}]
    sol = resolver(data)
    # salida 8:00, b a las 9:00, a a las 10:00, regreso 10:30 => 2.5 h * 60
    assert sol["desglose"]["salarios_horas"] == 150.0
    assert sol["rutas"][0]["sale_de_base"] == {"hora": "08:00"}
    assert sol["rutas"][0]["regresa_a_base"] == {"hora": "10:30"}

def test_descarga_desplaza_la_siguiente_llegada():
    # ventana puntual en "a" + salario por hora: todos los tiempos quedan
    # fijados por el optimo (salida 00:00, a las 00:30, b lo antes posible).
    data = _data(vehiculos=[vehiculo(salario_por_hora=60)])
    data["puntos"][0]["tiempo_descarga_min"] = 15
    data["puntos"][0]["ventanas"] = [{"desde": "00:30", "hasta": "00:30"}]
    sol = resolver(data)
    paradas = {p["punto"]: p for p in sol["rutas"][0]["paradas"]}
    assert paradas["a"]["fin_descarga"] == {"hora": "00:45"}
    assert paradas["b"]["llegada"] == {"hora": "01:15"}
    assert sol["fin_ultima_entrega"] == {"hora": "01:15"}

def test_turno_acota_la_ruta():
    data = _data(vehiculos=[vehiculo(turno={"desde": "09:00", "hasta": "11:00"})])
    sol = resolver(data)
    assert sol["rutas"][0]["sale_de_base"]["hora"] >= "09:00"
    assert sol["rutas"][0]["regresa_a_base"]["hora"] <= "11:00"
```

- [ ] **Step 2: Verificar rojo** — KeyError/AssertionError (no hay tiempos aún).

- [ ] **Step 3: Implementar** — en `construir_modelo`, insertar este bloque AL FINAL de la función, después de que exista la lista `costo` con los términos de arcos y fijos, dejando `m.costo_cent = sum(costo)` como última línea:

```python
    H = inst.horizonte_min
    m.makespan = m.model.NewIntVar(0, H, "makespan")
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
        salida = m.model.NewIntVar(v.turno_ini, v.turno_fin, f"salida_{v.id}")
        fin = m.model.NewIntVar(v.turno_ini, v.turno_fin, f"fin_{v.id}")
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
```

(mover el cierre `m.costo_cent = sum(costo)` al final de la función).

En `solver.py`:
```python
from exact_vrp.instancia import DIAS, MINUTOS_DIA, parsear_instancia

def _momento(minuto, modo):
    hora = f"{(minuto % MINUTOS_DIA) // 60:02d}:{minuto % 60:02d}"
    if modo == "un_dia":
        return {"hora": hora}
    return {"dia": DIAS[minuto // MINUTOS_DIA], "hora": hora}
```

En `_extraer`: por ruta usada añadir `"sale_de_base": _momento(solver.Value(m.salida[iv]), inst.modo)`; por parada `"llegada"` y `"fin_descarga"` (llegada + descarga); si `v.regresa_a_base`, `"regresa_a_base": _momento(solver.Value(m.fin_ruta[iv]), inst.modo)`; acumular `salarios_horas += v.salario_cent_min * (fin - salida) / 100` y sumarlo al `costo` de la ruta; al dict raíz añadir `"fin_ultima_entrega": _momento(max(solver.Value(m.llegada[p]) + inst.puntos[p].descarga_min for p in range(len(inst.puntos))), inst.modo)`.

- [ ] **Step 4: Verificar verde** — `.venv/bin/python -m pytest tests/ -v`

- [ ] **Step 5: Commit** — `git commit -m "exact: tiempos, ventanas, turnos y salario por hora"`

---

### Task 8: Modo `varios_dias` — ventanas semanales y fecha límite

**Files:**
- Create: `project/exact/tests/test_varios_dias.py`

**Interfaces:**
- Consumes: todo lo anterior (el modelo ya trabaja en minutos absolutos del horizonte; esta task VERIFICA el comportamiento semanal end-to-end y no debería requerir código nuevo — si algo falla, es un bug a arreglar donde corresponda).

- [ ] **Step 1: Tests (pueden pasar directo; si fallan, arreglar antes de seguir)**

`project/exact/tests/test_varios_dias.py`:
```python
from exact_vrp import resolver
from util import instancia_minima, vehiculo, punto

def _semanal(**kw):
    base = instancia_minima(modo="varios_dias", horizonte_dias=7,
                            vehiculos=[vehiculo()], puntos=[punto(id="a")])
    base.update(kw)
    return base

def test_entrega_el_dia_de_la_ventana():
    data = _semanal()
    data["puntos"][0]["ventanas"] = [{"dia": "jueves", "desde": "09:00", "hasta": "12:00"}]
    sol = resolver(data)
    assert sol["rutas"][0]["paradas"][0]["llegada"]["dia"] == "jueves"

def test_turno_del_camion_decide_el_dia():
    data = _semanal()
    data["puntos"][0]["ventanas"] = [
        {"dia": "martes", "desde": "09:00", "hasta": "12:00"},
        {"dia": "jueves", "desde": "09:00", "hasta": "12:00"}]
    data["vehiculos"][0]["turno"] = {"dia": "jueves", "desde": "08:00", "hasta": "17:00"}
    sol = resolver(data)
    assert sol["rutas"][0]["paradas"][0]["llegada"]["dia"] == "jueves"

def test_fecha_limite_fuerza_el_dia_temprano():
    data = _semanal()
    data["puntos"][0]["ventanas"] = [
        {"dia": "martes", "desde": "09:00", "hasta": "12:00"},
        {"dia": "viernes", "desde": "09:00", "hasta": "12:00"}]
    data["puntos"][0]["fecha_limite"] = {"dia": "miercoles", "hora": "12:00"}
    sol = resolver(data)
    assert sol["rutas"][0]["paradas"][0]["llegada"]["dia"] == "martes"

def test_salida_reporta_dia_y_hora():
    sol = resolver(_semanal())
    assert set(sol["rutas"][0]["sale_de_base"].keys()) == {"dia", "hora"}
```

- [ ] **Step 2: Ejecutar** — `.venv/bin/python -m pytest tests/test_varios_dias.py -v`. Si algún test falla, aplicar systematic-debugging (causa raíz en `instancia.py`/`modelo.py`) antes de continuar.

- [ ] **Step 3: Commit** — `git add project/exact && git commit -m "exact: cobertura del modo varios_dias"`

---

### Task 9: Rutas abiertas (`regresa_a_base: false`)

**Files:**
- Modify: `project/exact/exact_vrp/modelo.py` (ya contemplado en tiempos; falta el costo), `project/exact/exact_vrp/solver.py` (km y salida)
- Create: `project/exact/tests/test_ruta_abierta.py`

**Interfaces:**
- Produces: si `regresa_a_base` es false, el arco de cierre (i→0) no aporta costo, km, litros ni tiempo; la ruta no incluye el campo `regresa_a_base`.

- [ ] **Step 1: Tests en rojo**

`project/exact/tests/test_ruta_abierta.py`:
```python
from exact_vrp import resolver
from util import instancia_minima, vehiculo, punto

def test_abierta_no_paga_el_regreso():
    data = instancia_minima(vehiculos=[vehiculo(regresa_a_base=False)])
    sol = resolver(data)  # solo ida: 10 km * 0.1 = 1.0 (cerrada seria 2.0)
    assert sol["costo_total"] == 1.0
    assert sol["rutas"][0]["km"] == 10.0
    assert "regresa_a_base" not in sol["rutas"][0]

def test_cerrada_si_paga_el_regreso():
    assert resolver(instancia_minima())["costo_total"] == 2.0
```

- [ ] **Step 2: Verificar rojo** — la abierta hoy cobra el regreso (2.0 ≠ 1.0).

- [ ] **Step 3: Implementar** — en `construir_modelo`, al precalcular arcos, anular el cierre para vehículos abiertos:

```python
                    m.costo_arco[iv, i, j] = 0 if (j == 0 and not v.regresa_a_base) else round(
                        d * (v.consumo_litros_km * inst.precio_litro + v.salario_por_km) * 100)
```
(el `tiempo_arco` del cierre ya se ignora en `fin` vía el condicional `regreso` de la Task 7; dejarlo como está).

En `_extraer`, al recorrer los arcos, no sumar `km` del arco de cierre si el vehículo no regresa:
```python
            if not (siguiente == 0 and not v.regresa_a_base):
                km += inst.dist_km[nodo][siguiente]
```

- [ ] **Step 4: Verificar verde** — `.venv/bin/python -m pytest tests/ -v`

- [ ] **Step 5: Commit** — `git commit -m "exact: rutas abiertas sin costo de regreso"`

---

### Task 10: Objetivos `tiempo` y `costo_luego_tiempo`

**Files:**
- Modify: `project/exact/exact_vrp/solver.py`
- Create: `project/exact/tests/test_objetivos.py`

**Interfaces:**
- Produces: `resolver` respeta `objetivo`; lexicográfico = dos resoluciones (min costo → fijar `costo_cent ≤ C*` → min makespan). El dict de salida siempre reporta `costo_total` real (recalculado del desglose cuando el objetivo minimizado fue el makespan).

- [ ] **Step 1: Tests en rojo**

`project/exact/tests/test_objetivos.py`:
```python
from exact_vrp import resolver
from util import instancia_minima, vehiculo, punto

DOS = [[0, 10, 20], [10, 0, 10], [20, 10, 0]]

def _data(objetivo):
    data = instancia_minima(
        matriz_distancias_km=DOS, objetivo=objetivo,
        vehiculos=[vehiculo()],
        puntos=[punto(id="a", tiempo_descarga_min=30), punto(id="b")])
    return data

def test_lexicografico_desempata_por_makespan():
    # a->b y b->a cuestan igual (40 km); a->b termina en 00:50, b->a en 01:00
    sol = resolver(_data("costo_luego_tiempo"))
    assert sol["costo_total"] == 4.0
    assert sol["fin_ultima_entrega"] == {"hora": "00:50"}

def test_objetivo_tiempo_minimiza_makespan():
    sol = resolver(_data("tiempo"))
    assert sol["fin_ultima_entrega"] == {"hora": "00:50"}
    assert sol["costo_total"] == 4.0  # costo real reportado aunque no se optimice
```

- [ ] **Step 2: Verificar rojo** — con objetivo costo ambos órdenes son óptimos; el lexicográfico aún no existe (KeyError de objetivo o makespan 01:00 intermitente → el assert de 00:50 falla).

- [ ] **Step 3: Implementar** — en `resolver`, reemplazar el bloque Minimize/Solve:

```python
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = inst.limite_solver_s
    solver.parameters.num_workers = 8

    if inst.objetivo == "tiempo":
        m.model.Minimize(m.makespan)
        status = solver.Solve(m.model)
    elif inst.objetivo == "costo":
        m.model.Minimize(m.costo_cent)
        status = solver.Solve(m.model)
    else:  # costo_luego_tiempo
        m.model.Minimize(m.costo_cent)
        status = solver.Solve(m.model)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            m.model.Add(m.costo_cent <= round(solver.ObjectiveValue()))
            m.model.Minimize(m.makespan)
            status = solver.Solve(m.model)
```

En `_extraer`, no usar `solver.ObjectiveValue()` como costo: calcular
`costo_total` sumando el desglose (combustible + fijos + km + horas), que ya se
reconstruye de los arcos elegidos. `gap_relativo` se calcula solo cuando el
objetivo minimizado fue `costo_cent` (en `tiempo`/fase 2 reportar 0.0 si
OPTIMO; si FACTIBLE, el gap del makespan).

- [ ] **Step 4: Verificar verde** — `.venv/bin/python -m pytest tests/ -v`

- [ ] **Step 5: Commit** — `git commit -m "exact: objetivos tiempo y costo_luego_tiempo (lexicografico)"`

---

### Task 11: Estados no óptimos e infactibilidad del solver

**Files:**
- Modify: `project/exact/exact_vrp/solver.py`
- Create: `project/exact/tests/test_estados.py`

**Interfaces:**
- Produces: comportamiento verificado de `INFACTIBLE` (del solver, no del diagnóstico), mapeo de estados y `gap_relativo`. Además, TODA rama en la que el solver corrió incluye `tiempo_solver_s`, y `SIN_SOLUCION` incluye `motivo` accionable ("se agoto el limite de tiempo sin encontrar solucion; sube limite_tiempo_solver_s").

- [ ] **Step 1: Tests en rojo (o verdes: verificar)**

`project/exact/tests/test_estados.py`:
```python
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
```

- [ ] **Step 2: Ejecutar** — `.venv/bin/python -m pytest tests/test_estados.py -v`. El segundo test debe dar INFACTIBLE; si devolviera otra cosa, hay un bug de modelado a investigar con systematic-debugging. El assert de `tiempo_solver_s` queda en rojo hasta el Step 3.

- [ ] **Step 3: Uniformar la salida no exitosa** — en `resolver`, la rama de estados no exitosos queda exactamente así:

```python
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        salida = {"estado": _estado(status),
                  "tiempo_solver_s": round(solver.WallTime(), 2)}
        if salida["estado"] == "INFACTIBLE":
            salida["motivo"] = ("sin solucion que cumpla todas las restricciones "
                                "(combinacion de ventanas, turnos y flota)")
        else:
            salida["motivo"] = ("se agoto el limite de tiempo sin encontrar "
                                "solucion; sube limite_tiempo_solver_s")
        return salida
```

Verificar verde: `.venv/bin/python -m pytest tests/ -v`.

- [ ] **Step 4: Commit** — `git add project/exact && git commit -m "exact: estados del solver e infactibilidad"`

---

### Task 12: CLI, instancia de ejemplo, humo y README

**Files:**
- Create: `project/exact/run.py`, `project/exact/ejemplo_instancia.json`, `project/exact/tests/test_humo.py`, `project/exact/README.md`

**Interfaces:**
- Consumes: `resolver`.
- Produces: `python run.py instancia.json [salida.json]` — imprime resumen y escribe el JSON completo si se pasa salida.

- [ ] **Step 1: Test de humo en rojo**

`project/exact/tests/test_humo.py`:
```python
import json, pathlib
from exact_vrp import resolver

def test_ejemplo_realista_da_optimo():
    ruta = pathlib.Path(__file__).parent.parent / "ejemplo_instancia.json"
    data = json.loads(ruta.read_text())
    sol = resolver(data)
    assert sol["estado"] == "OPTIMO"
    entregados = sorted(p["punto"] for r in sol["rutas"] for p in r["paradas"])
    assert entregados == sorted(pt["id"] for pt in data["puntos"])
    assert sol["tiempo_solver_s"] < 60
```

- [ ] **Step 2: Crear `ejemplo_instancia.json`** — modo `varios_dias`, 15 puntos, 4 vehículos heterogéneos (uno abierto, uno con turno de un solo día, salarios mixtos: fijo/km/hora), ventanas en 3 días distintos, 2 puntos con `fecha_limite`, descargas de 5-15 min, matriz 16×16 generada de coordenadas aleatorias fijas (distancia euclídea redondeada a 1 decimal, escrita literal en el JSON — sin generación en runtime). Objetivo `costo_luego_tiempo`, límite 60 s.

- [ ] **Step 3: Verificar verde el humo** — `.venv/bin/python -m pytest tests/test_humo.py -v` (debe resolver OPTIMO en segundos).

- [ ] **Step 4: `run.py`**

```python
import json
import sys

from exact_vrp import resolver


def main():
    if len(sys.argv) < 2:
        print("uso: python run.py instancia.json [salida.json]")
        return 1
    with open(sys.argv[1]) as f:
        solucion = resolver(json.load(f))
    print(f"estado: {solucion['estado']}")
    if solucion["estado"] in ("OPTIMO", "FACTIBLE"):
        print(f"costo total: {solucion['costo_total']}  (gap {solucion['gap_relativo']})")
        for ruta in solucion["rutas"]:
            paradas = " -> ".join(p["punto"] for p in ruta["paradas"])
            print(f"  {ruta['vehiculo']}: base -> {paradas}"
                  + (" -> base" if "regresa_a_base" in ruta else "")
                  + f"  ({ruta['km']} km, {ruta['costo']})")
    elif "motivo" in solucion:
        print(f"motivo: {solucion['motivo']}")
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w") as f:
            json.dump(solucion, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Probar a mano: `.venv/bin/python run.py ejemplo_instancia.json` muestra las rutas.

- [ ] **Step 5: README** — secciones: qué es (solver exacto CP-SAT, certifica óptimo/gap); instalación (venv + requirements, nota del wheel de Python); uso como librería (`from exact_vrp import resolver`) y CLI; formato de entrada campo a campo con defaults (copiar del spec); formato de salida; patrón vehículo-día con ejemplo JSON de un camión listado lunes y martes; redondeos (minutos, centavos, gramos, litros); límites prácticos (~40 puntos óptimo probado, más allá FACTIBLE + gap; subir `limite_tiempo_solver_s`).

- [ ] **Step 6: Suite completa y commit final**

Run: `.venv/bin/python -m pytest tests/ -v` — Expected: TODOS PASS
```bash
cd /home/dario/daa && git add project/exact && git commit -m "exact: CLI, instancia de ejemplo y README"
```
