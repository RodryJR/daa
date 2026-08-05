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
