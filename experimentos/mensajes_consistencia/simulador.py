"""Simulador aislado: memoria, reloj virtual y un solo consumidor."""
from collections import Counter
from copy import deepcopy
from datetime import datetime
import heapq
import json

ESTADOS = {"pendiente", "confirmado", "no_asistire"}


def crear_mensaje(message_id, invitacion_id=101, estado="confirmado", version=1):
    return {
        "message_id": message_id,
        "event_type": "AsistenciaRespondida",
        "schema_version": 1,
        "occurred_at": "2026-10-26T02:00:00Z",
        "data": {"evento_id": 10, "invitacion_id": invitacion_id,
                 "estado": estado, "version_respuesta": version},
    }


def validar(mensaje):
    if not isinstance(mensaje, dict):
        raise ValueError("El mensaje debe ser un objeto")
    if not isinstance(mensaje.get("message_id"), str) or not mensaje["message_id"]:
        raise ValueError("message_id obligatorio")
    if mensaje.get("event_type") != "AsistenciaRespondida":
        raise ValueError("Tipo no soportado")
    if type(mensaje.get("schema_version")) is not int or mensaje["schema_version"] != 1:
        raise ValueError("Version de contrato no soportada")
    fecha = datetime.fromisoformat(mensaje.get("occurred_at", "").replace("Z", "+00:00"))
    if fecha.tzinfo is None:
        raise ValueError("occurred_at debe incluir zona horaria")
    datos = mensaje.get("data")
    if not isinstance(datos, dict):
        raise ValueError("data obligatorio")
    for campo in ("evento_id", "invitacion_id", "version_respuesta"):
        if type(datos.get(campo)) is not int or datos[campo] < 1:
            raise ValueError("Identificador/version invalido: " + campo)
    if datos.get("estado") not in ESTADOS:
        raise ValueError("Estado no soportado")


class Simulador:
    def __init__(self, fallos=None):
        self.ahora = 0
        self.cola = []
        self.secuencia = 0
        self.procesados = set()
        self.proyeccion = {}
        self.fallidos = []
        self.logs = []
        self.fallos = dict(fallos or {})

    def log(self, evento, mensaje, intento, **campos):
        self.logs.append({"event": evento, "message_id": mensaje.get("message_id"),
                          "attempt": intento, "virtual_time_seconds": self.ahora, **campos})

    def _encolar(self, mensaje, intento, demora=0):
        self.secuencia += 1
        heapq.heappush(self.cola, (self.ahora + demora, self.secuencia,
                                   intento, deepcopy(mensaje)))

    def publicar(self, mensaje):
        if not isinstance(mensaje, dict):
            raise ValueError("El productor requiere un objeto")
        self.log("message_produced", mensaje, 0)
        self._encolar(mensaje, 1)

    def _fallido(self, mensaje, intento, motivo):
        self.fallidos.append({"message": deepcopy(mensaje), "attempts": intento, "reason": motivo})
        self.log("message_dead_lettered", mensaje, intento, reason=motivo)

    def ejecutar(self):
        while self.cola:
            self.ahora, _, intento, mensaje = heapq.heappop(self.cola)
            self.log("message_delivered", mensaje, intento)
            try:
                validar(mensaje)
            except (ValueError, TypeError, AttributeError) as error:
                self._fallido(mensaje, intento, str(error))
                continue
            identificador = mensaje["message_id"]
            if identificador in self.procesados:
                self.log("duplicate_ignored", mensaje, intento)
                continue
            datos = mensaje["data"]
            clave = (datos["evento_id"], datos["invitacion_id"])
            anterior = self.proyeccion.get(clave)
            if anterior and datos["version_respuesta"] <= anterior[0]:
                self.procesados.add(identificador)
                self.log("stale_ignored", mensaje, intento)
                continue
            if self.fallos.get(identificador, 0) > 0:
                self.fallos[identificador] -= 1
                if intento < 3:
                    demora = 2 ** (intento - 1)
                    self.log("retry_scheduled", mensaje, intento, delay_seconds=demora)
                    self._encolar(mensaje, intento + 1, demora)
                else:
                    self._fallido(mensaje, intento, "Fallo temporal: intentos agotados")
                continue
            self.proyeccion[clave] = (datos["version_respuesta"], datos["estado"])
            self.procesados.add(identificador)
            self.log("message_processed", mensaje, intento)

    def resumen(self, evento_id=10):
        conteos = Counter(estado for (evento, _), (_, estado) in self.proyeccion.items()
                          if evento == evento_id)
        return {"total": sum(conteos.values()), "pendientes": conteos["pendiente"],
                "confirmados": conteos["confirmado"], "no_asistiran": conteos["no_asistire"]}

    def jsonl(self):
        return "\n".join(json.dumps(linea, ensure_ascii=False) for linea in self.logs)
