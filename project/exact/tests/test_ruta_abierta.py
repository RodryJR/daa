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
