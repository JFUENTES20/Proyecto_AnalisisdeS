from django.db import migrations


def copiar_perfiles(apps, schema_editor):
    alias = schema_editor.connection.alias
    Aspirante = apps.get_model("usuarios", "Aspirante")
    Perfil = apps.get_model("usuarios", "Perfil")
    for aspirante in Aspirante.objects.using(alias).all().iterator():
        Perfil.objects.using(alias).get_or_create(
            usuario_id=aspirante.user_id,
            defaults={"rol": "aspirante", "telefono": aspirante.telefono},
        )


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0002_perfil")]
    operations = [migrations.RunPython(copiar_perfiles, migrations.RunPython.noop)]
