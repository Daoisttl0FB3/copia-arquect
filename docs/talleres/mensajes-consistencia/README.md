# Taller: envio automatico de invitaciones

Reemplaza el resumen de Panel. Necesidad confirmada: enviar automaticamente los
enlaces desde EnAgenda. Prototipo aislado, sin envio real, Flask, BD ni Dokploy.
Correo simulado es un canal experimental, no un proveedor productivo elegido.

## Ejecutar

```bash
python -m unittest experimentos.mensajes_consistencia.test_simulador -v
python -m experimentos.mensajes_consistencia.demo
```

Solo biblioteca estandar. Pruebas junto al prototipo para no cargar conftest.py
de Flask/BD. El workflow taller-mensajes.yml ejecuta ambos comandos en Python
3.13 y guarda artefactos. Revisar su resultado; no se afirma CI verde.

## Contrato v1

```json
{"message_id":"msg-001","message_type":"EnviarInvitacion","schema_version":1,"data":{"envio_id":"envio-101","invitacion_id":101,"canal":"correo_simulado","destinatario":"invitado@example.invalid","enlace":"https://enagenda.example.invalid/invitacion/DEMO"}}
```

Todos los campos mostrados son obligatorios. IDs de mensaje/envio, destinatario
y enlace: cadenas no vacias. invitacion_id: entero positivo. Solo el tipo, canal
y version mostrados. No valida entregabilidad ni existencia del enlace. Datos
ficticios, sin credenciales. Campos opcionales adicionales son compatibles;
retirar campos o cambiar tipos/significado requiere nueva version mayor.
Version desconocida o contrato invalido va a fallidos sin reintentos.

message_id identifica un mensaje inmutable; envio_id, la solicitud logica.
Conservar ambos en reintentos y envio_id en republicaciones del mismo trabajo.
Un reenvio intencional requiere otro envio_id. No reutilizar claves con payload
diferente. Se deduplica por ambas claves despues de la aceptacion; el proveedor
simulado tambien es idempotente por envio_id. Aceptado no significa recibido.

## Entrega, reintentos y seguimiento

Entrega al menos una vez simulada dentro del proceso vivo, sin durabilidad.
Tres intentos totales, backoff 1 y 2 segundos, con reloj virtual. Fallos temporales
inyectados antes de aceptar. Tercer fallo: conservar original, intentos y motivo
en fallidos. No hay reintentos infinitos. Encolar no equivale a enviar: puede
haber trabajos pendientes o fallidos despues de registrar la solicitud.
Logs JSONL: message_id, envio_id, attempt, virtual_time_seconds; eventos desde
message_produced, message_delivered y provider_attempt hasta send_accepted,
retry_scheduled, duplicate_ignored o message_dead_lettered. Sin correo/enlace
en los logs. Los fallidos contienen payload ficticio; en produccion requieren
proteccion y politica de retencion.

## Artefactos y evidencia

- [Codigo](../../../experimentos/mensajes_consistencia/simulador.py)
- [Demo](../../../experimentos/mensajes_consistencia/demo.py)
- [Pruebas](../../../experimentos/mensajes_consistencia/test_simulador.py)
- [Ejecucion de pruebas](resultados/pruebas.txt)
- [Logs de demo](resultados/demo.jsonl)
- [ADR propuesto](../../adr/0004-evaluar-mensajeria-en-prototipo-aislado.md)
- [Workflow](../../../.github/workflows/taller-mensajes.yml)

Se reemplaza la evidencia de Panel. El asistente verifico la version inicial
del reemplazo con 11 pruebas exitosas en Python 3.12.8 y demo: 2 aceptaciones
simuladas, 1 duplicado, 3 reintentos y 1 fallido. Las salidas versionadas abajo
son un resumen de esa ejecucion previa; tras subir, CI debe producir la salida
detallada de la version final. No se verificaron suite completa, Actions ni
Dokploy. Enlazar commit final y run real antes de entregar.

## Limites

Memoria, un consumidor, sin red ni proveedor real. Sin concurrencia, persistencia,
outbox o atomicidad BD/publicacion. No prueba caida despues de aceptacion remota
y antes del registro local: un proveedor real sin idempotencia podria duplicar
el envio tras timeout. No promete exactamente una vez ni entrega al invitado.
Sin reproceso operativo de fallidos ni pruebas de carga. No se integra al MVP:
se pospone hasta definir proveedor, seguridad y estrategia durable, no porque
el envio carezca de necesidad.

## Apoyo de IA

2026-10-25, Perplexity. El usuario confirmo envio automatico y solicito sustituir
el prototipo de Panel. Se propuso EnviarInvitacion con proveedor simulado,
deduplicacion, reintentos y pruebas. Se corrige la justificacion: si hay necesidad
de envio; falta integracion productiva. Se descartan envios reales y credenciales
en el taller. Revision del equipo, CI final y aprobacion del ADR pendientes.
Este registro complementa docs/ia.md sin atribuir aprobaciones inexistentes.
