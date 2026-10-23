from typing import Protocol


class AlmacenDocumentos(Protocol):
    def abrir(self, referencia): ...


class DjangoStorageAdapter:
    """Adapter: convierte una referencia de dominio en un stream de Django Storage.

    La vista no necesita conocer rutas locales ni la implementación de almacenamiento.
    """

    def __init__(self, storage):
        self.storage = storage

    def abrir(self, referencia):
        return self.storage.open(referencia, "rb")
