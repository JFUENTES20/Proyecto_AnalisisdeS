from django.core.management.base import BaseCommand
from solicitudes.models import Solicitud


class Command(BaseCommand):
    help = 'Demuestra el patrón Observer con solicitudes de beca'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('DEMO: Patrón Observer - Plataforma Nacional de Becas'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        # Crear una solicitud
        self.stdout.write(self.style.WARNING('📝 Creando solicitud de beca...\n'))
        solicitud = Solicitud.objects.create(
            nombre='Juan García López',
            email='juan.garcia@example.com',
            estado='pendiente'
        )
        self.stdout.write(self.style.SUCCESS(f'✅ Solicitud creada: {solicitud}\n'))

        # Demostrar cambios de estado
        estados_secuencia = ['aprobada', 'activa', 'completada']
        
        for estado in estados_secuencia:
            input(f"\nPresiona ENTER para cambiar estado a '{estado}'...")
            solicitud.cambiar_estado(estado)

        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('✅ Demo completada'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
