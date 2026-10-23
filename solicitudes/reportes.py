"""Builder y Factory Method aplicados a la exportación de expedientes autorizados."""

import csv
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Reporte:
    encabezados: tuple
    filas: tuple


class ReporteBuilder:
    def __init__(self, solicitudes):
        self.solicitudes = solicitudes
        self.columnas = []

    def identificacion(self):
        self.columnas.extend(
            [
                ("Expediente", lambda s: f"BEC-{s.pk:05d}"),
                ("Convocatoria", lambda s: str(s.convocatoria or "Legado")),
            ]
        )
        return self

    def seguimiento(self):
        self.columnas.extend(
            [
                ("Estado", lambda s: s.get_estado_display()),
                ("Monto", lambda s: str(s.monto)),
            ]
        )
        return self

    def construir(self):
        if not self.columnas:
            raise ValueError("Selecciona al menos una sección del reporte.")
        return Reporte(
            tuple(c[0] for c in self.columnas),
            tuple(
                tuple(func(s) for _, func in self.columnas) for s in self.solicitudes
            ),
        )


class DocumentoCSV:
    def representar(self, reporte):
        salida = io.StringIO()
        escritor = csv.writer(salida)

        def segura(valor):
            texto = str(valor)
            return (
                "'" + texto
                if texto.lstrip().startswith(("=", "+", "-", "@"))
                else texto
            )

        escritor.writerow(reporte.encabezados)
        escritor.writerows([[segura(v) for v in fila] for fila in reporte.filas])
        return "\ufeff" + salida.getvalue()


class Exportador(ABC):
    @abstractmethod
    def crear_documento(self):
        """Factory Method: la subclase elige el producto de salida."""

    def exportar(self, reporte):
        return self.crear_documento().representar(reporte)


class ExportadorCSV(Exportador):
    def crear_documento(self):
        return DocumentoCSV()
