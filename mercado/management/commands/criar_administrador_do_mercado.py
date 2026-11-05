# Cria o primeiro administrador do mercado.
# Uso: definir MERCADO_ADMIN_USUARIO e MERCADO_ADMIN_SENHA e rodar
#   python manage.py criar_administrador_do_mercado

import os
from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from mercado.models import PerfilDeAcesso


def credenciais_do_mercado() -> tuple[str, str]:
    return (
        os.environ.get("MERCADO_ADMIN_USUARIO", "").strip(),
        os.environ.get("MERCADO_ADMIN_SENHA", ""),
    )


class Command(BaseCommand):
    help = "Cria o administrador do mercado se MERCADO_ADMIN_* estiverem definidas e ele não existir."

    def handle(self, *args: Any, **options: Any) -> None:
        usuario, senha = credenciais_do_mercado()
        if not usuario or not senha:
            self.stdout.write(
                "MERCADO_ADMIN_USUARIO/SENHA vazias; administrador do mercado não criado."
            )
            return
        if User.objects.filter(username=usuario).exists():
            self.stdout.write(f"Usuário {usuario!r} já existe; nada a fazer.")
            return
        criado = User.objects.create_user(username=usuario, password=senha)
        PerfilDeAcesso.objects.create(usuario=criado, administrador=True)
        self.stdout.write(
            self.style.SUCCESS(f"Administrador do mercado {usuario!r} criado.")
        )
