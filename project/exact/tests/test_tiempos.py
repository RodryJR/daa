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
