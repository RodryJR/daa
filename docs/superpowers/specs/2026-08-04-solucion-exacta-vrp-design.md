# Solución exacta al VRP con flota heterogénea, capacidad 2D y horarios semanales

Fecha: 2026-08-04
Estado: aprobado por Dario

## Objetivo

Módulo Python exacto (prueba optimalidad) para calcular las rutas de reparto de
una empresa: qué camiones salen, en qué orden visitan los puntos y a qué hora,
minimizando el gasto real (combustible + salarios) y, opcionalmente, el tiempo
de terminación. Debe ser gratuito, embebible en un sistema existente vía
librería + JSON, y rápido para instancias operativas.

## Decisión de tecnología

**CP-SAT (Google OR-Tools)**, licencia Apache 2.0.

- Es el solver exacto gratuito más potente disponible; paraleliza y certifica
  optimalidad o cota de gap.
- Alternativas descartadas: MILP con HiGHS/CBC (mucho más lento en ruteo),
  Branch & Bound propio (no escala más allá de ~15 puntos), Branch-Cut-and-Price
  académico (sistema de investigación impracticable de reimplementar).
- Riesgo: disponibilidad de wheel de `ortools` para Python 3.14. Plan B: el
  venv se crea con `python3.13` si está disponible; se documenta en el README.

## Estructura

```
project/exact/
├── exact_vrp/
│   ├── __init__.py       # exporta resolver()
│   ├── instancia.py      # parseo y validación del JSON de entrada
│   ├── modelo.py         # construcción del modelo CP-SAT
│   ├── solver.py         # resolver(instancia) -> solucion
│   └── diagnostico.py    # pre-chequeos de factibilidad
├── tests/
├── ejemplo_instancia.json
├── run.py                # CLI: python run.py instancia.json [salida.json]
├── requirements.txt
└── README.md
```

API pública: `resolver(instancia: dict) -> dict`. Sin estado global, sin I/O
dentro del solver (el CLI lee/escribe archivos; la librería solo dicts).

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

Reglas:

- El índice 0 de `matriz_distancias_km` es la base (depósito único). El punto
  i-ésimo de `puntos` corresponde a la fila/columna i+1. La matriz puede ser
  asimétrica; se valida cuadrada, no negativa y con diagonal 0.
- `modo = "un_dia"`: `ventanas`, `turno` y `fecha_limite` omiten el campo
  `dia`; el horizonte es un día (1440 min). `modo = "varios_dias"`: `dia` es
  obligatorio en ventanas/turnos/límites, con valores `lunes`..`domingo`, y el
  horizonte arranca lunes 00:00 con `horizonte_dias` días (por defecto 7).
- Campos opcionales y por defecto: `salario_*` = 0, `regresa_a_base` = true,
  `turno` = sin restricción (todo el horizonte), `tiempo_descarga_min` = 0,
  `fecha_limite` = sin límite, `ventanas` = [] significa sin restricción de
  recepción, `objetivo` = "costo", `limite_tiempo_solver_s` = 60,
  `horizonte_dias` = 7.
- Un punto sin productos es un error de validación.
- **Patrón vehículo-día** (camión que sale varios días): se lista el mismo
  camión físico una vez por día disponible, cada entrada con su `turno` de ese
  día. Cada entrada hace a lo sumo una ruta; el salario fijo se cobra por
  salida. Documentado en el README con ejemplo.

## Formato de salida

```json
{
  "estado": "OPTIMO" | "FACTIBLE" | "INFACTIBLE" | "SIN_SOLUCION",
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

En modo `un_dia` los campos de tiempo omiten `dia`. Si `regresa_a_base` es
false, la ruta no incluye ese campo. Las ventanas acotan el INICIO de la
descarga, así que los eventos de cierre (fin de descarga, regreso a base)
pueden caer pasado el fin del horizonte: en ese caso el momento incluye
`"dia_siguiente": true` (modo un_dia, cruzó medianoche) o
`"semana_siguiente": true` (varios_dias con horizonte de 7 días, el nombre
del día vuelve a empezar). Sin desborde, esos campos no aparecen. `INFACTIBLE` incluye `motivo` con el
diagnóstico. `FACTIBLE` = se agotó el límite de tiempo: mejor solución
encontrada + `gap_relativo` certificado (cota superior de distancia al óptimo).
`SIN_SOLUCION` = se agotó el límite sin encontrar solución ni probar
infactibilidad; el remedio es subir `limite_tiempo_solver_s`.

## Modelo CP-SAT

- **Enteros y redondeo**: tiempos en minutos; dinero en centavos; distancias en
  centésimas de km. Tiempo de viaje por arco y vehículo:
  `round(dist_km / velocidad_kmh * 60)` min. Costo por arco y vehículo:
  `round(dist_km * (consumo * precio + salario_por_km) * 100)` centavos.
  Salario por hora: `round(salario_por_hora * 100 / 60)` centavos/min ×
  duración de ruta en minutos. El redondeo se documenta en el README.
- **Ruteo**: un `AddCircuit` por vehículo sobre arcos opcionales
  (base → puntos → base); literal de self-loop = punto no visitado por ese
  vehículo. Cada punto: exactamente un vehículo lo visita. Literal
  `usado[v]` = el vehículo sale (arco desde base activo).
- **Capacidades**: Σ peso de puntos asignados ≤ capacidad_peso[v]; ídem
  volumen. Productos de un punto viajan juntos (no hay entrega dividida).
- **Tiempos**: variable `llegada[p]` en [0, horizonte); si arco (i→j) de v
  activo: `llegada[j] ≥ fin_descarga[i] + viaje_v(i,j)` (OnlyEnforceIf).
  `salida_base[v]` y `fin_ruta[v]` acotadas por el `turno` del vehículo.
  Ventanas semanales → intervalos absolutos [ini, fin) del horizonte; un
  booleano por ventana, exactamente uno activo si el punto tiene ventanas, y
  la llegada cae dentro del elegido. `fecha_limite` → cota superior dura de
  `llegada[p]` (la espera del camión ante un punto que aún no abre está
  permitida: llegada = comienzo de la descarga dentro de la ventana).
- **Ruta abierta**: si `regresa_a_base[v]` es false, el arco de cierre al
  depósito existe (el circuito lo exige) pero con costo y tiempo 0.
- **Objetivo**: `Σ_v (fijo_v·usado[v] + costo_arcos_v + tarifa_min_v·duración_v)`.
  Modos: `costo` (una resolución), `tiempo` (minimiza
  `max_p fin_descarga[p]`), `costo_luego_tiempo` (lexicográfico exacto: 1ª
  resolución minimiza costo C*; 2ª fija costo ≤ C* y minimiza el makespan de
  entregas). La solución de la 1ª fase se pasa como pista (warm start) a la
  2ª; si aun así la 2ª fase no termina dentro del límite, se devuelve la
  solución de costo óptimo de la 1ª fase con el campo `nota` explicando que
  el desempate por tiempo quedó incompleto (nunca se descarta una solución
  encontrada).

## Diagnóstico de infactibilidad (pre-chequeos)

Antes del solver, con mensajes accionables que incluyen los ids implicados:

1. Punto cuyo peso o volumen no cabe en ningún vehículo.
2. Demanda total que excede la capacidad agregada de la flota.
3. Punto con `fecha_limite` anterior a su primera ventana, o ventanas fuera
   del horizonte.
4. Punto inalcanzable dentro de toda ventana (viaje base→punto con el vehículo
   más rápido llega después del cierre de todas).
5. Matriz mal formada (no cuadrada, negativos, diagonal ≠ 0, dimensión ≠
   1 + cantidad de puntos).

Si aun así CP-SAT reporta INFEASIBLE, se devuelve `INFACTIBLE` con la lista de
restricciones más probables (combinación ventanas + turnos + flota).

## Testing (TDD)

1. Validación de instancia: errores claros por cada campo mal formado.
2. Conversión de ventanas semanales a intervalos absolutos (incluye un_dia).
3. Casos exactos verificables a mano (2-4 puntos): usa 1 camión vs 2 según
   fijo/consumo; elige el camión barato; respeta peso Y volumen por separado;
   respeta ventana semanal y fecha límite; ruta abierta más barata que
   cerrada cuando conviene; lexicográfico reduce makespan sin subir costo.
4. Cada pre-chequeo de diagnóstico dispara con su mensaje.
5. Humo: ~15 puntos, 4 vehículos heterogéneos → `OPTIMO` en segundos.

## Extensiones futuras (fuera de v1)

Múltiples depósitos; incompatibilidad producto-vehículo (refrigerados);
entregas opcionales con penalización (elegir qué posponer cuando no cabe
todo); matriz de tiempos explícita (tráfico) en lugar de velocidad constante;
multi-viaje nativo (hoy: patrón vehículo-día).
