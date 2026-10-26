# 0004 - Evaluar mensajeria en un prototipo aislado

- Estado: propuesto, pendiente de aprobacion del equipo.
- Fecha: 2026-10-25.
- Decide: equipo EnAgenda (revision pendiente).
- Alcance: experimento de resumen de asistencia, no sistema productivo.

## Contexto

El taller exige demostrar contrato, entrega, duplicados, reintentos y fallidos.
No se ha aportado una medicion que justifique desacoplar este resumen en el MVP.
El prototipo no altera los circuitos actuales de invitaciones.

## Alternativas

A. Consulta sincrona a traves de un caso de uso del contexto dueno: menos piezas,
lectura del estado confirmado y sin cola que operar. Depende del tiempo y
 disponibilidad del camino de consulta. Es la propuesta para mantener el MVP.

B. Mensajeria y proyeccion asincrona: separa temporalmente el procesamiento,
permite reintentos y evita que un trabajo secundario bloquee al productor.
Asume consistencia eventual, duplicados, estado durable adicional y operacion
de mensajes fallidos. Un broker no elimina la necesidad de idempotencia.

## Decision propuesta

No incorporar por ahora mensajeria al MVP. Construir y verificar un simulador
local aislado dentro del mismo repositorio, con biblioteca estandar. El equipo
debe aprobar o corregir esta propuesta. No se afirma que ya exista un resumen
sincrono integrado ni una cola desplegada.

## Consecuencias

El prototipo simula al menos una entrega dentro del proceso, hasta tres intentos
con backoff 1/2 segundos y fallidos. Deduplica por message_id y aplica solo la
ultima version por invitacion. Demuestra las reglas sin costo de infraestructura
adicional, pero no valida durabilidad, concurrencia ni atomicidad con PostgreSQL.
Reconsiderar la decision si hay trabajo secundario costoso, requisitos de segundo
plano o mediciones que justifiquen el desacoplamiento. Una integracion futura
requiere estrategia durable y tratamiento de caidas entre escritura/publicacion.

## Trazabilidad

- [Contrato, ejecucion y limites](../talleres/mensajes-consistencia/README.md).
- [Codigo](../../experimentos/mensajes_consistencia/simulador.py).
- [Pruebas](../../experimentos/mensajes_consistencia/test_simulador.py).
- [Workflow](../../.github/workflows/taller-mensajes.yml).
