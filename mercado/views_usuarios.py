# Login, troca de senha e cadastro de usuários do mercado.
# As telas de /usuarios/ só abrem para o administrador do mercado.

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

from .autorizacao import exigir_administrador
from .forms_usuarios import FormularioNovoUsuario


class TelaDeLogin(LoginView):
    """Tela de login. Quem já está logado vai direto para o painel."""

    template_name = "login.html"
    redirect_authenticated_user = True


# Sair não exige login para o usuário do /admin/ também conseguir sair
@method_decorator(login_not_required, name="dispatch")
class Sair(LogoutView):
    """Encerra a sessão (só por POST)."""

    next_page = reverse_lazy("entrar")


class TrocarMinhaSenha(SuccessMessageMixin, PasswordChangeView):
    """Usuário troca a própria senha."""

    template_name = "senha_propria.html"
    success_url = reverse_lazy("painel")
    success_message = "Senha alterada."


def usuarios_do_mercado() -> QuerySet[User]:
    """Só os usuários que têm perfil do mercado (o admin do Django fica de fora)."""
    return User.objects.filter(perfil_mercado__isnull=False).select_related(
        "perfil_mercado"
    )


@exigir_administrador
def listar_usuarios(request: HttpRequest) -> HttpResponse:
    """Lista de usuários do mercado."""
    usuarios = usuarios_do_mercado().order_by("username")
    return render(request, "usuarios/lista.html", {"usuarios": usuarios})


@exigir_administrador
def criar_usuario(request: HttpRequest) -> HttpResponse:
    """Cadastro de um novo usuário do mercado."""
    formulario = FormularioNovoUsuario(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        usuario = formulario.save()
        messages.success(request, f"Usuário {usuario.username} criado.")
        return redirect("usuarios")
    return render(request, "usuarios/novo.html", {"formulario": formulario})


@exigir_administrador
def definir_senha_usuario(request: HttpRequest, usuario_id: int) -> HttpResponse:
    """Administrador define uma nova senha para o usuário."""
    usuario = get_object_or_404(usuarios_do_mercado(), pk=usuario_id)
    formulario = SetPasswordForm(usuario, request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        # Se trocou a própria senha, mantém logado
        if usuario == request.user:
            update_session_auth_hash(request, usuario)
        messages.success(request, f"Senha de {usuario.username} alterada.")
        return redirect("usuarios")
    contexto = {"formulario": formulario, "usuario_alvo": usuario}
    return render(request, "usuarios/senha.html", contexto)


@exigir_administrador
@require_POST
def alternar_ativo_usuario(request: HttpRequest, usuario_id: int) -> HttpResponse:
    """Desativa ou reativa o usuário."""
    usuario = get_object_or_404(usuarios_do_mercado(), pk=usuario_id)
    if usuario == request.user:
        messages.error(request, "Você não pode desativar a si mesmo.")
        return redirect("usuarios")
    usuario.is_active = not usuario.is_active
    usuario.save(update_fields=["is_active"])
    situacao = "reativado" if usuario.is_active else "desativado"
    messages.success(request, f"Usuário {usuario.username} {situacao}.")
    return redirect("usuarios")
