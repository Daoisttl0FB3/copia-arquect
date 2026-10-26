import unittest
from .simulador import ProveedorSimulado, Simulador, crear_mensaje


class PruebasEnvios(unittest.TestCase):
    def procesar(self, mensajes, fallos=None):
        s = Simulador(ProveedorSimulado(fallos))
        for m in mensajes:
            s.publicar(m)
        s.ejecutar()
        return s

    def test_envio_exitoso(self):
        self.assertEqual(self.procesar([crear_mensaje("a")]).resumen()["accepted_sends"], 1)

    def test_duplicado(self):
        m = crear_mensaje("a")
        s = self.procesar([m, m])
        self.assertEqual(s.proveedor.intentos["envio-101"], 1)
        self.assertEqual(s.resumen()["duplicates"], 1)

    def test_mismo_envio_otro_mensaje(self):
        s = self.procesar([crear_mensaje("a"), crear_mensaje("b")])
        self.assertEqual(s.proveedor.intentos["envio-101"], 1)

    def test_recuperable(self):
        s = self.procesar([crear_mensaje("a")], {"envio-101": 1})
        self.assertEqual(s.proveedor.intentos["envio-101"], 2)
        self.assertEqual(len(s.enviados), 1)
        self.assertEqual(s.fallidos, [])

    def test_backoff_fallidos(self):
        s = self.procesar([crear_mensaje("a")], {"envio-101": 3})
        self.assertEqual([x["virtual_time_seconds"] for x in s.logs if x["event"] == "provider_attempt"], [0, 1, 3])
        self.assertEqual([x["delay_seconds"] for x in s.logs if x["event"] == "retry_scheduled"], [1, 2])
        self.assertEqual(s.fallidos[0]["attempts"], 3)
        self.assertEqual(len(s.enviados), 0)
        self.assertNotIn("a", s.procesados)

    def test_opcional(self):
        m = crear_mensaje("a")
        m["extra"] = True
        m["data"]["extra"] = True
        self.assertEqual(len(self.procesar([m]).enviados), 1)

    def test_version(self):
        m = crear_mensaje("a")
        m["schema_version"] = 2
        s = self.procesar([m])
        self.assertEqual(s.fallidos[0]["attempts"], 1)
        self.assertEqual(s.proveedor.intentos, {})

    def test_obligatorio(self):
        m = crear_mensaje("a")
        del m["data"]["enlace"]
        s = self.procesar([m])
        self.assertEqual(len(s.fallidos), 1)
        self.assertEqual(s.proveedor.intentos, {})

    def test_canal(self):
        m = crear_mensaje("a")
        m["data"]["canal"] = "otro"
        self.assertEqual(len(self.procesar([m]).fallidos), 1)

    def test_trazabilidad(self):
        s = self.procesar([crear_mensaje("a")])
        self.assertEqual({x["message_id"] for x in s.logs}, {"a"})
        self.assertEqual(s.logs[-1]["event"], "send_accepted")
        self.assertNotIn("example.invalid", s.jsonl())

    def test_proveedor_idempotente(self):
        p = ProveedorSimulado()
        d = crear_mensaje("a")["data"]
        self.assertEqual(p.enviar(d), p.enviar(d))
        self.assertEqual(len(p.aceptados), 1)


if __name__ == "__main__":
    unittest.main()
