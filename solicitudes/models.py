from django.db import models
from .patterns import GestorObservadores, NotificadorEmail, NotificadorSistema, NotificadorAdmin


class Solicitud(models.Model):
    """Modelo de solicitud de beca - Subject del patrón Observer"""
    
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('activa', 'Activa'),
        ('completada', 'Completada'),
        ('rechazada', 'Rechazada'),
    ]
    
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    email = models.EmailField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Instancia del gestor de observadores
    _gestor = GestorObservadores()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Inicializar observadores cuando se crea una solicitud
        if not self._gestor._observadores:
            self._gestor.agregar_observador(NotificadorEmail())
            self._gestor.agregar_observador(NotificadorSistema())
            self._gestor.agregar_observador(NotificadorAdmin())
    
    def cambiar_estado(self, nuevo_estado):
        """Cambia el estado y notifica a los observadores"""
        if nuevo_estado in dict(self.ESTADOS):
            print(f"\n{'='*60}")
            print(f"🔄 CAMBIO DE ESTADO: {self.estado.upper()} → {nuevo_estado.upper()}")
            print(f"{'='*60}\n")
            
            self.estado = nuevo_estado
            self._gestor.notificar(self)
            self.save()
        else:
            print(f"❌ Estado inválido: {nuevo_estado}")
    
    def __str__(self):
        return f"Solicitud #{self.id} - {self.nombre} ({self.estado})"
    
    class Meta:
        verbose_name = "Solicitud"
        verbose_name_plural = "Solicitudes"
        ordering = ['-fecha_creacion']
