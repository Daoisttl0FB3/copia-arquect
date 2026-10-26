# 0004 - Evaluar envio asincrono de invitaciones con proveedor simulado

- Estado: propuesto, pendiente del equipo.
- Fecha: 2026-10-25.
- Decide: equipo EnAgenda (revision pendiente).
- Pieza: envio automatico de enlaces de invitacion.

## Contexto

El usuario confirmo envio automatico desde EnAgenda. Se sustituye el borrador
de resumen de Panel. Existe necesidad funcional de envio y dependencia externa
con posibles fallos; no se afirma que ya este implementada en produccion.

## Alternativas

A. Sincrona: el caso de uso llama al proveedor durante la solicitud web. Menos
piezas y resultado inmediato de aceptacion/rechazo; la espera y fallos afectan
la respuesta web. Requiere controlar duplicados y timeouts ambiguos.

B. Asincrona: registrar trabajo y procesarlo despues. Permite reintentos sin
retener la solicitud web; separa guardar invitacion de intentar su envio.
Agrega consistencia eventual, cola durable, fallidos y seguimiento. Encolar
no equivale a entrega final.

## Decision propuesta

Evaluar B en un prototipo aislado con proveedor simulado. No integrar aun en
Flask o Dokploy hasta definir proveedor, seguridad, idempotencia y persistencia.
No se rechaza el requisito de envio ni la utilidad de una cola. El equipo debe
aprobar o corregir esta propuesta.

## Consecuencias

Al menos una entrega simulada dentro del proceso; deduplicacion por message_id
y envio_id; tres intentos con backoff 1/2 segundos y fallidos. Proveedor simulado
idempotente; un reenvio intencional usa nuevo envio_id. Sin durabilidad ni
atomicidad con PostgreSQL. No demuestra entrega real ni exactamente una vez.
Un fallo tras aceptacion remota requiere idempotencia del proveedor o
reconciliacion, no solo un conjunto local. No requiere pagos ni credenciales.

## Trazabilidad

- [Contrato, evidencia y limites](../talleres/mensajes-consistencia/README.md)
- [Codigo](../../experimentos/mensajes_consistencia/simulador.py)
- [Pruebas](../../experimentos/mensajes_consistencia/test_simulador.py)

Se reemplaza un borrador propuesto, no una decision aceptada historica.
