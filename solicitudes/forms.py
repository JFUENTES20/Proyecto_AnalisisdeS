from io import BytesIO
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from django import forms


class SolicitudForm(forms.Form):
    monto = forms.DecimalField(
        label="Monto solicitado", max_digits=12, decimal_places=2, min_value=0.01
    )
    motivacion = forms.CharField(
        label="Cuéntanos por qué solicitas esta beca",
        min_length=30,
        max_length=5000,
        widget=forms.Textarea(attrs={"rows": 5}),
    )


class DocumentoForm(forms.Form):
    nombre = forms.CharField(label="Nombre del documento", max_length=160)
    archivo = forms.FileField(label="Archivo PDF, JPG o PNG (máximo 10 MB)")

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if archivo.size > 10 * 1024 * 1024:
            raise forms.ValidationError("El archivo supera los 10 MB.")
        extension = Path(archivo.name).suffix.lower()
        contenido = archivo.read()
        archivo.seek(0)
        if extension == ".pdf":
            valido = contenido.startswith(b"%PDF-")
        elif extension in {".jpg", ".jpeg", ".png"}:
            try:
                imagen = Image.open(BytesIO(contenido))
                esperado = "PNG" if extension == ".png" else "JPEG"
                valido = imagen.format == esperado
                imagen.verify()
            except (
                UnidentifiedImageError,
                OSError,
                SyntaxError,
                Image.DecompressionBombError,
            ):
                valido = False
        else:
            valido = False
        if not valido:
            raise forms.ValidationError("El archivo debe ser un PDF, JPG o PNG válido.")
        return archivo


class AccionForm(forms.Form):
    accion = forms.ChoiceField(
        choices=[
            (a, a)
            for a in (
                "enviar",
                "revisar",
                "corregir",
                "aprobar",
                "rechazar",
                "activar",
                "completar",
            )
        ]
    )
    comentario = forms.CharField(required=False, max_length=4000, widget=forms.Textarea)


class EvaluacionForm(forms.Form):
    puntaje = forms.IntegerField(
        label="Puntuación (0 a 100)", min_value=0, max_value=100
    )
    observaciones = forms.CharField(
        label="Fundamentación de la evaluación",
        min_length=10,
        max_length=4000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
