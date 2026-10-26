"""Envio automatico simulado: sin red ni credenciales."""
from copy import deepcopy
import heapq
import json


def crear_mensaje(message_id, envio_id="envio-101"):
    return {"message_id": message_id, "message_type": "EnviarInvitacion",
            "schema_version": 1, "data": {"envio_id": envio_id,
            "invitacion_id": 101, "canal": "correo_simulado",
            "destinatario": "invitado@example.invalid",
            "enlace": "https://enagenda.example.invalid/invitacion/DEMO"}}


def validar(m):
    if not isinstance(m.get("message_id"), str) or not m["message_id"]:
        raise ValueError("message_id obligatorio")
    if m.get("message_type") != "EnviarInvitacion":
        raise ValueError("Tipo no soportado")
    if type(m.get("schema_version")) is not int or m["schema_version"] != 1:
        raise ValueError("Version no soportada")
    d = m.get("data")
    if not isinstance(d, dict):
        raise ValueError("data obligatorio")
    for campo in ("envio_id", "destinatario", "enlace"):
        if not isinstance(d.get(campo), str) or not d[campo].strip():
            raise ValueError("Campo obligatorio: " + campo)
    if type(d.get("invitacion_id")) is not int or d["invitacion_id"] < 1:
        raise ValueError("invitacion_id invalido")
    if d.get("canal") != "correo_simulado":
        raise ValueError("Canal no soportado")


class FalloTemporal(Exception):
    pass


class ProveedorSimulado:
    def __init__(self, fallos=None):
        self.fallos = dict(fallos or {})
        self.intentos = {}
        self.aceptados = {}

    def enviar(self, datos):
        clave = datos["envio_id"]
        self.intentos[clave] = self.intentos.get(clave, 0) + 1
        if clave in self.aceptados:
            return self.aceptados[clave]
        if self.fallos.get(clave, 0) > 0:
            self.fallos[clave] -= 1
            raise FalloTemporal("Proveedor temporalmente no disponible")
        self.aceptados[clave] = "sim-" + clave
        return self.aceptados[clave]


class Simulador:
    def __init__(self, proveedor=None):
        self.proveedor = proveedor if proveedor is not None else ProveedorSimulado()
        self.ahora = 0
        self.cola = []
        self.secuencia = 0
        self.procesados = set()
        self.enviados = {}
        self.fallidos = []
        self.logs = []

    def log(self, evento, m, intento, **extra):
        self.logs.append({"event": evento, "message_id": m.get("message_id"),
                          "envio_id": m.get("data", {}).get("envio_id") if isinstance(m.get("data"), dict) else None,
                          "attempt": intento, "virtual_time_seconds": self.ahora, **extra})

    def _encolar(self, m, intento, demora=0):
        self.secuencia += 1
        heapq.heappush(self.cola, (self.ahora + demora, self.secuencia, intento, deepcopy(m)))

    def publicar(self, m):
        if not isinstance(m, dict):
            raise ValueError("Se requiere un objeto")
        self.log("message_produced", m, 0)
        self._encolar(m, 1)

    def _fallido(self, m, intento, motivo):
        self.fallidos.append({"message": deepcopy(m), "attempts": intento, "reason": motivo})
        self.log("message_dead_lettered", m, intento, reason=motivo)

    def ejecutar(self):
        while self.cola:
            self.ahora, _, intento, m = heapq.heappop(self.cola)
            self.log("message_delivered", m, intento)
            try:
                validar(m)
            except (ValueError, TypeError, AttributeError) as error:
                self._fallido(m, intento, str(error))
                continue
            mid, datos = m["message_id"], m["data"]
            clave = datos["envio_id"]
            if mid in self.procesados or clave in self.enviados:
                self.procesados.add(mid)
                self.log("duplicate_ignored", m, intento)
                continue
            self.log("provider_attempt", m, intento)
            try:
                recibo = self.proveedor.enviar(datos)
            except FalloTemporal as error:
                if intento < 3:
                    demora = 2 ** (intento - 1)
                    self.log("retry_scheduled", m, intento, delay_seconds=demora)
                    self._encolar(m, intento + 1, demora)
                else:
                    self._fallido(m, intento, str(error))
                continue
            self.enviados[clave] = recibo
            self.procesados.add(mid)
            self.log("send_accepted", m, intento, provider_receipt=recibo)

    def resumen(self):
        return {"accepted_sends": len(self.enviados),
                "duplicates": sum(x["event"] == "duplicate_ignored" for x in self.logs),
                "retries": sum(x["event"] == "retry_scheduled" for x in self.logs),
                "dead_letters": len(self.fallidos)}

    def jsonl(self):
        return "\n".join(json.dumps(x, ensure_ascii=False) for x in self.logs)
