"""Ejecutar desde la raiz: python -m experimentos.mensajes_consistencia.demo."""
import json
from .simulador import Simulador, crear_mensaje


def main():
    simulador = Simulador(fallos={"msg-recuperable": 1, "msg-agotado": 3})
    normal = crear_mensaje("msg-normal")
    for mensaje in (normal, normal,
                    crear_mensaje("msg-recuperable", invitacion_id=102),
                    crear_mensaje("msg-agotado", invitacion_id=103)):
        simulador.publicar(mensaje)
    simulador.ejecutar()
    print(simulador.jsonl())
    print(json.dumps({"event": "experiment_summary", "resumen": simulador.resumen(),
                      "duplicates": sum(x["event"] == "duplicate_ignored" for x in simulador.logs),
                      "retries": sum(x["event"] == "retry_scheduled" for x in simulador.logs),
                      "dead_letters": len(simulador.fallidos)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
