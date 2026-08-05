# exact_vrp

Solver **exacto** (no heurístico) para el problema de ruteo de vehículos (VRP)
con flota heterogénea, capacidad 2D (peso y volumen), horarios semanales y
salarios. Calcula qué camiones salen, en qué orden visitan los puntos y a qué
hora, minimizando el costo real (combustible + salarios) y, opcionalmente, el
tiempo de terminación.

## Qué es

Usa [CP-SAT](https://developers.google.com/optimization/cp/cp_solver) (Google
OR-Tools), un solver de programación por restricciones de licencia Apache 2.0.
A diferencia de una heurística, CP-SAT **certifica** la solución: si el estado
es `OPTIMO`, esa es matemáticamente la mejor solución posible (no "una buena
solución"); si se agota el tiempo antes de probarlo, devuelve la mejor
encontrada junto con `gap_relativo`, una cota superior certificada de qué tan
lejos puede estar del óptimo.

Es una librería Python embebible (`resolver(dict) -> dict`, sin estado global
ni I/O) más una CLI de conveniencia para correrla desde archivos JSON.

## Instalación

```bash
cd project/exact
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

`requirements.txt` trae `ortools>=9.15` (única dependencia de runtime) y
`pytest>=8` (para correr la suite de tests).

**Nota sobre el wheel de Python**: OR-Tools publica wheels precompilados solo
para un subconjunto de versiones de CPython; si tu intérprete es muy nuevo,
`pip install` puede no encontrar un wheel y caer a compilar desde fuente (lento
o directamente inviable). En el entorno de desarrollo de este proyecto,
`python3.14.6` con `ortools==9.15.6755` instaló y corrió sin problemas — pero
si tu `pip install` falla por falta de wheel, crea el venv con una versión
algo más antigua (p. ej. `python3.13`) mientras OR-Tools publica soporte para
la tuya.

Verificar la instalación corriendo la suite:

```bash
.venv/bin/python -m pytest tests/ -v
```

## Uso

### Como librería

```python
from exact_vrp import resolver

solucion = resolver({
    "matriz_distancias_km": [[0, 10], [10, 0]],
    "precio_combustible_litro": 1.30,
    "vehiculos": [{"id": "camion-1", "capacidad_peso_kg": 500,
                   "capacidad_volumen_m3": 3, "velocidad_kmh": 50}],
    "puntos": [{"id": "cliente-1",
                "productos": [{"peso_kg": 20, "volumen_m3": 0.2}]}]
})
print(solucion["estado"])  # "OPTIMO"
```

`resolver` recibe y devuelve `dict` puros (el resultado de `json.load`/lo que
espera `json.dump`); no toca el disco ni guarda estado entre llamadas, así que
es seguro embeberlo en otro sistema (un endpoint HTTP, un job programado,
etc.) y llamarlo repetidamente con instancias distintas.

### Como CLI

```bash
.venv/bin/python run.py instancia.json                # imprime un resumen
.venv/bin/python run.py instancia.json salida.json     # + escribe el JSON completo
```

Ejemplo real, contra `ejemplo_instancia.json` (15 puntos, 4 vehículos
heterogéneos — ver más abajo):

```
$ .venv/bin/python run.py ejemplo_instancia.json
estado: OPTIMO
costo total: 206.05  (gap 0.0)
  camion-frio: base -> cliente-01 -> cliente-02 -> cliente-06 -> cliente-08 -> cliente-13 -> cliente-14 -> base  (105.9 km, 71.45)
  camion-ligero: base -> cliente-03 -> cliente-07 -> cliente-09 -> cliente-10 -> cliente-15 -> base  (86.9 km, 44.49)
  camion-lunes: base -> cliente-04 -> cliente-05 -> base  (39.5 km, 49.85)
  camion-abierto: base -> cliente-11 -> cliente-12  (37.1 km, 40.26)
```

Nótese que `camion-abierto` no termina en `-> base`: tiene
`regresa_a_base: false`, así que el CLI no le agrega el regreso.

## Formato de entrada

```json
{
  "modo": "varios_dias",
  "horizonte_dias": 7,
  "matriz_distancias_km": [[0, 12.5], [12.5, 0]],
  "precio_combustible_litro": 1.30,
  "objetivo": "costo_luego_tiempo",
  "limite_tiempo_solver_s": 60,
  "vehiculos": [{
      "id": "camion-1",
      "capacidad_peso_kg": 3500,
      "capacidad_volumen_m3": 12,
      "consumo_litros_km": 0.18,
      "velocidad_kmh": 45,
      "salario_fijo": 500,
      "salario_por_km": 0,
      "salario_por_hora": 40,
      "regresa_a_base": true,
      "turno": {"dia": "lunes", "desde": "08:00", "hasta": "17:00"}
  }],
  "puntos": [{
      "id": "cliente-7",
      "productos": [{"peso_kg": 30, "volumen_m3": 0.2}],
      "tiempo_descarga_min": 10,
      "ventanas": [{"dia": "martes", "desde": "09:00", "hasta": "13:00"}],
      "fecha_limite": {"dia": "miercoles", "hora": "18:00"}
  }]
}
```

### Campos de nivel superior

| Campo | Tipo | Default | Notas |
|---|---|---|---|
| `modo` | `"un_dia"` \| `"varios_dias"` | `"un_dia"` | ver abajo |
| `horizonte_dias` | entero 1-7 | `7` | solo aplica si `modo="varios_dias"` |
| `matriz_distancias_km` | matriz cuadrada `(1+N)×(1+N)` | — (obligatorio) | índice `0` = base; puede ser asimétrica; se valida cuadrada, no negativa y diagonal `0` |
| `precio_combustible_litro` | número ≥ 0 | `0` | |
| `objetivo` | `"costo"` \| `"tiempo"` \| `"costo_luego_tiempo"` | `"costo"` | ver [Objetivos](#objetivos) |
| `limite_tiempo_solver_s` | número ≥ 0 | `60` | segundos que CP-SAT puede usar; ver [Límites prácticos](#límites-prácticos-y-rendimiento) |
| `vehiculos` | lista, ≥ 1 | — (obligatorio) | |
| `puntos` | lista, ≥ 1 | — (obligatorio) | |

`modo="un_dia"`: `ventanas`, `turno` y `fecha_limite` **omiten** el campo
`dia`; el horizonte es un día (1440 min). `modo="varios_dias"`: `dia` es
**obligatorio** en ventanas/turnos/límites, con valores `lunes`..`domingo`
(sin acentos), y el horizonte arranca lunes 00:00 con `horizonte_dias` días.

### Campos de cada vehículo

| Campo | Tipo | Default | Notas |
|---|---|---|---|
| `id` | string | — (obligatorio) | único; no puede repetirse ni coincidir con un id de punto |
| `capacidad_peso_kg` | número > 0 | — (obligatorio) | |
| `capacidad_volumen_m3` | número > 0 | — (obligatorio) | |
| `consumo_litros_km` | número ≥ 0 | `0` | |
| `velocidad_kmh` | número > 0 | — (obligatorio) | |
| `salario_fijo` | número ≥ 0 | `0` | se cobra una vez si el vehículo sale (ver [patrón vehículo-día](#patrón-vehículo-día)) |
| `salario_por_km` | número ≥ 0 | `0` | |
| `salario_por_hora` | número ≥ 0 | `0` | tarifa por la duración total de la ruta (salida → cierre) |
| `regresa_a_base` | bool | `true` | si es `false`, la ruta queda "abierta": el arco de cierre existe (el circuito lo exige) pero con costo y tiempo `0` |
| `turno` | `{dia, desde, hasta}` | sin restricción (todo el horizonte) | acota `salida_base` y `fin_ruta`; **es un límite duro** — ver nota abajo |

Un `turno` **explícito** es un límite duro: la ruta entera (salida, todas las
entregas, cierre) debe caber dentro de `[desde, hasta]`. Si **no** se da
`turno`, el vehículo puede operar en todo el horizonte, y como no hay límite
que lo tope, el cierre de su ruta (última descarga + regreso, si aplica)
puede terminar después del fin nominal del horizonte — ver los marcadores
`dia_siguiente`/`semana_siguiente` en [Formato de salida](#formato-de-salida).

### Campos de cada punto

| Campo | Tipo | Default | Notas |
|---|---|---|---|
| `id` | string | — (obligatorio) | único |
| `productos` | lista de `{peso_kg, volumen_m3}`, ≥ 1 | — (obligatorio, no vacía) | un punto sin productos es error de validación; los productos de un punto viajan juntos (sin entrega dividida) |
| `tiempo_descarga_min` | número ≥ 0 | `0` | |
| `ventanas` | lista de `{dia, desde, hasta}` | `[]` (sin restricción) | si hay ≥ 1, la llegada debe caer dentro de exactamente una de ellas |
| `fecha_limite` | `{dia, hora}` | sin límite | cota superior dura de la llegada; si el punto tiene ventanas, debe ser posterior al inicio de la más temprana (si no, error de validación) |

## Formato de salida

```json
{
  "estado": "OPTIMO",
  "gap_relativo": 0.0,
  "costo_total": 1234.56,
  "desglose": {"combustible": 800.00, "salarios_fijos": 300.00,
               "salarios_km": 0.0, "salarios_horas": 134.56},
  "fin_ultima_entrega": {"dia": "martes", "hora": "16:40"},
  "rutas": [{
      "vehiculo": "camion-1",
      "sale_de_base": {"dia": "martes", "hora": "08:12"},
      "paradas": [{"punto": "cliente-7",
                   "llegada": {"dia": "martes", "hora": "09:00"},
                   "fin_descarga": {"dia": "martes", "hora": "09:10"}}],
      "regresa_a_base": {"dia": "martes", "hora": "10:05"},
      "km": 84.2, "litros": 15.2,
      "peso_cargado_kg": 350, "volumen_cargado_m3": 1.4,
      "costo": 310.20
  }],
  "vehiculos_sin_usar": ["camion-2"],
  "tiempo_solver_s": 3.2
}
```

En modo `un_dia` los campos de tiempo omiten `dia`. Si `regresa_a_base` del
vehículo es `false`, la ruta no incluye ese campo.

### Estados

- **`OPTIMO`**: CP-SAT probó optimalidad. `gap_relativo` es `0.0`.
- **`FACTIBLE`**: se agotó `limite_tiempo_solver_s` con la mejor solución
  encontrada hasta ese momento; `gap_relativo` es la cota superior
  certificada de qué tan lejos puede estar del óptimo real.
- **`INFACTIBLE`**: no existe solución que cumpla todas las restricciones.
  Trae `motivo`. Hay dos rutas posibles a este estado, con formas de salida
  distintas: si lo detecta el **pre-diagnóstico** (antes de invocar CP-SAT),
  la salida es solo `{"estado": "INFACTIBLE", "motivo": "..."}` — **sin**
  `tiempo_solver_s`, porque el solver ni llega a correr. Si el
  pre-diagnóstico no detecta nada pero CP-SAT prueba infactibilidad al
  modelar, la salida sí incluye `tiempo_solver_s` además de `motivo`.
- **`SIN_SOLUCION`**: se agotó el tiempo sin encontrar ninguna solución ni
  probar infactibilidad. Trae `motivo` y `tiempo_solver_s`; el remedio es
  subir `limite_tiempo_solver_s`.

Para `OPTIMO`/`FACTIBLE` la salida completa (`costo_total`, `desglose`,
`rutas`, `vehiculos_sin_usar`, `fin_ultima_entrega`, `tiempo_solver_s`,
`gap_relativo`) siempre está presente.

### Eventos que caen fuera del horizonte

Las ventanas acotan el **inicio** de la descarga, no su fin: un punto puede
tener ventana hasta las 23:55 con 10 minutos de descarga y ser perfectamente
válido aunque la descarga termine a las 00:05. Por eso los eventos de
*cierre* — `fin_descarga` de la última parada y `regresa_a_base` — pueden caer
pasado el fin nominal del horizonte. Cuando eso pasa, el momento trae un
campo extra marcando el desborde:

- Modo `un_dia`: `"dia_siguiente": true` si cruzó la medianoche.
- Modo `varios_dias`: `"semana_siguiente": true` si cruzó el fin de la
  semana (el nombre del día vuelve a empezar en `lunes`).

Sin desborde, esos campos simplemente no aparecen. Esto es más probable
cuando un vehículo **no** tiene `turno` explícito (ver nota en
[campos de vehículo](#campos-de-cada-vehículo)), porque entonces no hay techo
que impida que el cierre de la ruta se corra más allá del horizonte nominal.

## Objetivos

- **`costo`**: una sola resolución, minimiza el costo total.
- **`tiempo`**: minimiza el *makespan* (`max` de `fin_descarga` sobre todos
  los puntos). El `costo_total` reportado es el costo real de esa solución,
  aunque no sea el que se optimizó.
- **`costo_luego_tiempo`**: lexicográfico en **dos fases**, cada una con su
  propio presupuesto de `limite_tiempo_solver_s` completo — en el peor caso
  el total puede tardar hasta **~2×** el límite configurado. La fase 1
  minimiza el costo (da `C*`); la fase 2 fija `costo ≤ C*` y minimiza el
  makespan, arrancando con la solución de la fase 1 como pista (*warm
  start*). `tiempo_solver_s` en la salida final refleja **solo la última
  fase resuelta**, no la suma de ambas. Si la fase 2 no termina dentro de su
  límite, nunca se descarta la solución de costo óptimo ya encontrada: se
  devuelve la solución de la fase 1 (óptima en costo, sin desempate de
  tiempo) con un campo `nota` explicando que el desempate quedó incompleto —
  en ese caso `tiempo_solver_s` corresponde a la fase 1.

## Patrón vehículo-día

El modelo resuelve **una** ruta por entrada de vehículo (un solo `AddCircuit`
por vehículo, sobre todo el horizonte). Si un camión físico sale varios días
distintos —regresando a base entre uno y otro—, no se modela como un vehículo
con múltiples viajes: se **lista el mismo camión una vez por cada día
disponible**, cada entrada con su propio `id` y su propio `turno` acotado a
ese día. Cada entrada puede hacer a lo sumo una ruta, y **el salario fijo se
cobra por salida**: si las dos entradas terminan usándose, `salario_fijo` se
paga dos veces.

```json
{
  "vehiculos": [
    {
      "id": "camion-3-lunes",
      "capacidad_peso_kg": 2000,
      "capacidad_volumen_m3": 10,
      "consumo_litros_km": 0.20,
      "velocidad_kmh": 50,
      "salario_fijo": 30,
      "turno": {"dia": "lunes", "desde": "08:00", "hasta": "17:00"}
    },
    {
      "id": "camion-3-martes",
      "capacidad_peso_kg": 2000,
      "capacidad_volumen_m3": 10,
      "consumo_litros_km": 0.20,
      "velocidad_kmh": 50,
      "salario_fijo": 30,
      "turno": {"dia": "martes", "desde": "08:00", "hasta": "17:00"}
    }
  ]
}
```

`camion-3-lunes` y `camion-3-martes` son el mismo camión físico (misma
capacidad, consumo, velocidad y tarifa) modelado como dos vehículos
independientes en la instancia. El solver decide, para cada entrada por
separado, si le conviene salir o no (`vehiculos_sin_usar` puede incluir una,
ambas, o ninguna). Si en cambio se listara **un solo** vehículo sin `turno`
(o con un turno que abarque ambos días), el modelo lo trataría como **una**
ruta continua que podría visitar puntos del lunes y del martes sin pasar por
la base entre medio — y `salario_fijo` se cobraría una sola vez —, lo cual no
representa a un camión que vuelve a su base cada noche.

## Redondeos

Para que el modelo sea exacto en aritmética entera (CP-SAT no usa punto
flotante en las restricciones), todo se redondea al construir el modelo:

- **Minutos**: el tiempo de viaje de cada arco, por vehículo, es
  `round(distancia_km / velocidad_kmh * 60)`.
- **Centavos**: el costo de cada arco, por vehículo, es
  `round(distancia_km * (consumo_litros_km * precio_combustible_litro +
  salario_por_km) * 100)`. El salario por hora se convierte a centavos por
  minuto (`round(salario_por_hora * 100 / 60)`) y se multiplica por los
  minutos de duración de la ruta.
- **Gramos y litros de capacidad**: `capacidad_peso_kg` de cada vehículo se
  convierte a gramos (`× 1000`) y `capacidad_volumen_m3` a litros
  (`× 1000`) para trabajar en enteros; lo mismo para el peso y volumen
  totales de cada punto (la suma en punto flotante de sus `productos`, recién
  convertida y redondeada una vez a nivel del punto). Esto es distinto de
  `litros` en la salida de cada ruta, que son litros de **combustible**
  consumidos (`km × consumo_litros_km`), no volumen de carga.

`costo_total` en la salida es la **suma del desglose** (`combustible +
salarios_fijos + salarios_km + salarios_horas`, cada uno ya redondeado a 2
decimales). En instancias con un solo vehículo esto coincide exactamente con
la suma de `costo` de cada ruta, pero con **flotas de 2+ vehículos y
consumos fraccionarios** puede diferir en ±1 centavo de esa suma, por
acumulación independiente de redondeos — no es un error, es la diferencia
entre redondear la suma y sumar los redondeados.

## Límites prácticos y rendimiento

CP-SAT resuelve instancias de este tamaño de forma exacta y rápida, pero
sigue siendo un problema NP-difícil: el tiempo de resolución crece con la
cantidad de puntos, vehículos y restricciones activas (ventanas, turnos,
capacidad). Como referencia:

- Instancias de hasta **~15 puntos** con flota heterogénea (como
  `ejemplo_instancia.json`, incluida en este directorio) resuelven a
  `OPTIMO` en **menos de un segundo a pocos segundos**.
- Instancias de hasta **~40 puntos** típicamente siguen probando `OPTIMO` en
  **segundos a minutos**.
- Más allá de eso (o con instancias particularmente restringidas: ventanas
  muy ajustadas combinadas con muchos vehículos intercambiables, alta
  simetría de costos, etc.), es esperable que el estado sea `FACTIBLE` en
  vez de `OPTIMO` dentro del límite de tiempo por defecto — la solución
  sigue siendo válida y viene con `gap_relativo` certificado. El remedio es
  subir `limite_tiempo_solver_s` (recordando que con `objetivo:
  "costo_luego_tiempo"` el límite aplica **por fase**, así que el tiempo
  total puede llegar a ~2× lo configurado).

Una observación práctica del desarrollo de este proyecto: instancias con
**muchos puntos sin ventana** (totalmente libres de horario) y vehículos sin
costo por hora tienden a ser más lentas de resolver a `OPTIMO` que
instancias con ventanas ajustadas, aunque tengan el mismo tamaño — más
libertad de horario significa más soluciones distintas con el mismo costo,
y CP-SAT tiene que explorar ese espacio para probar optimalidad del
desempate de tiempo. Ventanas más ajustadas *ayudan* al solver, no lo
complican.

## Instancia de ejemplo

`ejemplo_instancia.json` es una instancia realista y resoluble: modo
`varios_dias` (horizonte de 5 días, lunes a viernes), 15 puntos, 4 vehículos
heterogéneos —

- `camion-frio`: 700 kg / 5 m³, salario fijo, sin turno (toda la semana).
- `camion-ligero`: 500 kg / 3.5 m³, salario por km, sin turno.
- `camion-lunes`: 650 kg / 4.5 m³, salario fijo + por hora, **turno acotado
  al lunes**.
- `camion-abierto`: 750 kg / 5.5 m³, salario por hora, **`regresa_a_base:
  false`**.

Las capacidades están deliberadamente ajustadas: ningún par de vehículos
cubre la demanda total (1670 kg / 12 m³) por sí solo, así que la solución
óptima necesita usar los 4.

— con ventanas repartidas en lunes/miércoles/viernes, 2 puntos con
`fecha_limite` además de su ventana, descargas de 5 a 15 minutos, matriz
16×16 de distancias euclídeas (coordenadas fijas, redondeadas a 1 decimal) y
objetivo `costo_luego_tiempo` con límite de 60 s. Resuelve a `OPTIMO`
usando los 4 vehículos en bien menos de un segundo (ver la salida de
ejemplo en [Uso → CLI](#como-cli)). `tests/test_humo.py` la corre como
prueba de humo del paquete completo.
