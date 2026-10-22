def rol_de(usuario):
    if not usuario.is_authenticated:
        return ""
    if usuario.is_superuser:
        return "administrador"
    perfil = getattr(usuario, "perfil", None)
    return perfil.rol if perfil else ""


def es_personal(usuario):
    return rol_de(usuario) in {"evaluador", "aprobador", "administrador"}
