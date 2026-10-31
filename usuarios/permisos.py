from django.contrib.auth import get_user_model


def cuenta_activa(usuario):
    """Consultar la vigencia actual, incluso si el llamador conserva un User viejo."""
    return bool(
        usuario.is_authenticated
        and usuario.is_active
        and get_user_model().objects.filter(pk=usuario.pk, is_active=True).exists()
    )


def rol_de(usuario):
    if not cuenta_activa(usuario):
        return ""
    if usuario.is_superuser:
        return "administrador"
    perfil = getattr(usuario, "perfil", None)
    return perfil.rol if perfil else ""


def es_personal(usuario):
    return rol_de(usuario) in {"evaluador", "aprobador", "administrador"}
