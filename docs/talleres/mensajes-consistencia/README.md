# Taller aplicado: Mensajes y consistencia

Prototipo aislado del MVP de EnAgenda. No cambia Flask, PostgreSQL ni Dokploy.
La propuesta simula Invitaciones -> cola -> proyeccion de asistencia para Panel.
No contiene datos personales, tokens de invitacion ni credenciales.

## Ejecutar desde la raiz

```bash
python -m unittest experimentos.mensajes_consistencia.test_simulador -v
python -m experimentos.mensajes_consistencia.demo
```

Solo requiere biblioteca estandar de Python. Las pruebas estan junto al prototipo
para ejecutarlas sin cargar tests/conftest.py ni las dependencias de Flask/BD.
El workflow independiente taller-mensajes.yml prueba Python 3.13 y guarda logs
como artefactos; no implica que el CI general o el despliegue esten verificados.

## Artefactos navegables

- [Simulador](../../../experimentos/mensajes_consistencia/simulador.py)
- [Demo](../../../experimentos/mensajes_consistencia/demo.py)
- [Pruebas](../../../experimentos/mensajes_consistencia/test_simulador.py)
- [ADR propuesto](../../adr/0004-evaluar-mensajeria-en-prototipo-aislado.md)
- [Salida real de la demo](resultados/demo.jsonl)
- [Salida real de pruebas](resultados/pruebas.txt)
- [Workflow](../../../.github/workflows/taller-mensajes.yml)

## Contrato v1

```json
{"message_id":"msg-001","event_type":"AsistenciaRespondida","schema_version":1,"occurred_at":"2026-10-26T02:00:00Z","data":{"evento_id":10,"invitacion_id":101,"estado":"confirmado","version_respuesta":1}}
```

Todos los campos mostrados son obligatorios. message_id es una cadena no vacia
que identifica un evento inmutable y se conserva durante reentregas. Los IDs y
version_respuesta son enteros positivos. occurred_at incluye zona horaria.
Estados permitidos: pendiente, confirmado, no_asistire.
La fecha de ejemplo es sintetica; no representa la fecha real de una operacion.

Compatibilidad: v1 admite campos opcionales adicionales. Eliminar campos,
cambiar tipos o significados requiere nueva version mayor. El consumidor solo
acepta v1. Contratos invalidos y versiones desconocidas van a fallidos sin
reintentar. Una version_respuesta mayor sustituye el estado anterior por
invitacion; versiones iguales o anteriores se ignoran. El productor debe emitir
una nueva version cuando cambia la respuesta y no reutilizar message_id.

## Entrega, consistencia y fallos

Se simula entrega al menos una vez dentro del proceso: los reintentos conservan
message_id. No se promete entrega durable ante reinicios. La proyeccion puede
estar desactualizada mientras hay mensajes pendientes; si todos los cambios
validos llegan y se aplican, converge al ultimo estado recibido por version.
Mensajes en fallidos requieren revision; no hay convergencia garantizada si se
abandona un cambio sin procesar.

Deduplicacion mediante conjunto de message_id procesados, actualizado despues
del efecto. El resumen cuenta invitaciones, no mensajes. Reintentos: tres
intentos totales, demoras de 1 y 2 segundos; el tercer fallo envia el original,
intentos y motivo a una cola de fallidos. Sin reintentos infinitos. Backoff con
reloj virtual, no esperas reales. Fallos temporales inyectados antes del efecto.

Los logs JSONL enlazan message_produced, message_delivered, retry_scheduled,
message_processed, duplicate_ignored, stale_ignored y message_dead_lettered por
message_id, con attempt y virtual_time_seconds. La demo resume contadores.

## Evidencia ejecutada y pendiente

El asistente ejecuto el prototipo en un entorno Python aislado, no sobre el
repositorio completo: 11 pruebas exitosas. La demo obtuvo 2 confirmados, 1
duplicado ignorado, 3 reintentos y 1 mensaje fallido. Las salidas reales estan en
resultados/. La version de Python utilizada figura en pruebas.txt.
No se ejecuto la suite completa, no se verifico Dokploy ni un run de Actions.
Tras subir, el equipo debe revisar el workflow y enlazar su run y el commit de
entrega. No se afirma que esas verificaciones ya hayan ocurrido.

## Limites

Cola, deduplicacion, proyeccion y fallidos en memoria, perdidos al reiniciar.
Un solo consumidor, sin concurrencia ni pruebas de carga. Sin broker real,
outbox, atomicidad con PostgreSQL ni recuperacion ante caida entre efecto y
registro de deduplicacion. No evalua particiones de red, disco o indisponibilidad
real. No implementa reproceso operativo de fallidos. Los IDs del evento y de la
invitacion deben ser estables en una integracion futura. No incorpora el patron
al sistema desplegado. La no incorporacion es una propuesta pendiente del equipo.

## Registro del apoyo de IA

Fecha: 2026-10-25. Herramienta: Perplexity. Se genero el simulador, demo, pruebas,
workflow y documentacion como propuesta. Se corrigio el diseno inicial para
sustituir estados por version y no contar respuestas sucesivas como personas
nuevas. Se descarto incorporar un broker o modificar el MVP sin necesidad
medida, para limitar complejidad y riesgo. Se verificaron las 11 pruebas y la
demo en entorno aislado. Aceptacion final, CI y aprobacion del ADR: pendientes
del equipo. Este registro complementa docs/ia.md sin atribuirle una aprobacion
que todavia no existe.
