"""
Patrón Observer - Notificación de cambios de estado en solicitudes de beca
"""

from abc import ABC, abstractmethod
from datetime import datetime


class Observer(ABC):
    """Interfaz base para observadores"""
    
    @abstractmethod
    def actualizar(self, solicitud):
        """Método que se ejecuta cuando cambia el estado"""
        pass


class NotificadorEmail(Observer):
    """Observador que simula envío de email"""
    
    def actualizar(self, solicitud):
        print(f"📧 EMAIL: Se envió notificación a {solicitud.email}")
        print(f"   Asunto: Su solicitud de beca fue {solicitud.estado}")
        print(f"   Timestamp: {datetime.now()}\n")


class NotificadorSistema(Observer):
    """Observador que registra en el sistema"""
    
    def actualizar(self, solicitud):
        print(f"💾 SISTEMA: Cambio registrado en base de datos")
        print(f"   Solicitud ID: {solicitud.id}")
        print(f"   Nuevo estado: {solicitud.estado}")
        print(f"   Timestamp: {datetime.now()}\n")


class NotificadorAdmin(Observer):
    """Observador que notifica al administrador"""
    
    def actualizar(self, solicitud):
        print(f"👤 ADMIN: Alerta para administrador")
        print(f"   Solicitante: {solicitud.nombre}")
        print(f"   Acción: {solicitud.estado}")
        print(f"   Timestamp: {datetime.now()}\n")


class GestorObservadores:
    """Gestor de observadores para las solicitudes"""
    
    def __init__(self):
        self._observadores = []
    
    def agregar_observador(self, observador: Observer):
        """Añade un observador a la lista"""
        if observador not in self._observadores:
            self._observadores.append(observador)
            print(f"✅ Observador agregado: {observador.__class__.__name__}\n")
    
    def remover_observador(self, observador: Observer):
        """Remueve un observador"""
        if observador in self._observadores:
            self._observadores.remove(observador)
    
    def notificar(self, solicitud):
        """Notifica a todos los observadores"""
        for observador in self._observadores:
            observador.actualizar(solicitud)
