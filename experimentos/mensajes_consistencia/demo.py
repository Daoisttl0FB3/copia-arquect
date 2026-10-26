import json
from .simulador import ProveedorSimulado, Simulador, crear_mensaje


def main():
    s = Simulador(ProveedorSimulado({"envio-recuperable": 1, "envio-agotado": 3}))
    normal = crear_mensaje("msg-normal", "envio-normal")
    for m in (normal, normal, crear_mensaje("msg-recuperable", "envio-recuperable"),
              crear_mensaje("msg-agotado", "envio-agotado")):
        s.publicar(m)
    s.ejecutar()
    print(s.jsonl())
    print(json.dumps({"event": "experiment_summary", **s.resumen()}))


if __name__ == "__main__":
    main()
