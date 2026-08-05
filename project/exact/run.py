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
