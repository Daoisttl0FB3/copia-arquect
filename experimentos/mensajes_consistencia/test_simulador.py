import unittest
from .simulador import Simulador, crear_mensaje


class PruebasMensajes(unittest.TestCase):
    def test_duplicado_tiene_un_solo_efecto(self):
        s = Simulador()
        m = crear_mensaje("a")
        s.publicar(m)
        s.publicar(m)
        s.ejecutar()
        self.assertEqual(s.resumen()["confirmados"], 1)
        self.assertEqual(sum(x["event"] == "duplicate_ignored" for x in s.logs), 1)

    def test_fallo_recuperable(self):
        s = Simulador({"a": 1})
        s.publicar(crear_mensaje("a"))
        s.ejecutar()
        self.assertEqual(s.resumen()["total"], 1)
        self.assertEqual(s.fallidos, [])
        self.assertEqual([x["attempt"] for x in s.logs if x["event"] == "message_processed"], [2])

    def test_backoff_y_agotamiento(self):
        s = Simulador({"a": 3})
        s.publicar(crear_mensaje("a"))
        s.ejecutar()
        self.assertEqual([x["virtual_time_seconds"] for x in s.logs if x["event"] == "message_delivered"], [0, 1, 3])
        self.assertEqual([x["delay_seconds"] for x in s.logs if x["event"] == "retry_scheduled"], [1, 2])
        self.assertEqual(s.fallidos[0]["attempts"], 3)
        self.assertEqual(s.resumen()["total"], 0)
        self.assertNotIn("a", s.procesados)

    def test_campo_opcional_es_compatible(self):
        s = Simulador()
        m = crear_mensaje("a")
        m["extra"] = "opcional"
        m["data"]["extra"] = "opcional"
        s.publicar(m)
        s.ejecutar()
        self.assertEqual(s.resumen()["total"], 1)

    def test_version_no_soportada_no_se_reintenta(self):
        s = Simulador()
        m = crear_mensaje("a")
        m["schema_version"] = 2
        s.publicar(m)
        s.ejecutar()
        self.assertEqual(s.fallidos[0]["attempts"], 1)
        self.assertFalse(any(x["event"] == "retry_scheduled" for x in s.logs))

    def test_campo_obligatorio_ausente(self):
        s = Simulador()
        m = crear_mensaje("a")
        del m["data"]["invitacion_id"]
        s.publicar(m)
        s.ejecutar()
        self.assertEqual(len(s.fallidos), 1)

    def test_estado_invalido(self):
        s = Simulador()
        s.publicar(crear_mensaje("a", estado="otro"))
        s.ejecutar()
        self.assertEqual(len(s.fallidos), 1)

    def test_respuesta_nueva_sustituye_anterior(self):
        s = Simulador()
        s.publicar(crear_mensaje("a"))
        s.publicar(crear_mensaje("b", estado="no_asistire", version=2))
        s.ejecutar()
        self.assertEqual(s.resumen(), {"total": 1, "pendientes": 0, "confirmados": 0, "no_asistiran": 1})

    def test_version_antigua_no_revierte_estado(self):
        s = Simulador()
        s.publicar(crear_mensaje("b", estado="no_asistire", version=2))
        s.publicar(crear_mensaje("a"))
        s.ejecutar()
        self.assertEqual(s.resumen()["no_asistiran"], 1)
        self.assertTrue(any(x["event"] == "stale_ignored" for x in s.logs))

    def test_seguimiento_identificador(self):
        s = Simulador({"a": 1})
        s.publicar(crear_mensaje("a"))
        s.ejecutar()
        self.assertEqual({x["message_id"] for x in s.logs}, {"a"})
        self.assertEqual(s.logs[0]["event"], "message_produced")
        self.assertEqual(s.logs[-1]["event"], "message_processed")

    def test_tipo_de_identificador_invalido(self):
        s = Simulador()
        m = crear_mensaje("a")
        m["data"]["evento_id"] = True
        s.publicar(m)
        s.ejecutar()
        self.assertEqual(len(s.fallidos), 1)


if __name__ == "__main__":
    unittest.main()
