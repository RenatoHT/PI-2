# Depois do login, confere se o usuário tem perfil do mercado.
# Quem entra com a conta do /admin/ do Django vê a tela "sem acesso".

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .autorizacao import tem_acesso_ao_painel


class ExigirPerfilDoMercadoMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_view(
        self,
        request: HttpRequest,
        view_func: Callable[..., HttpResponse],
        view_args: tuple[object, ...],
        view_kwargs: dict[str, object],
    ) -> HttpResponse | None:
        if self._view_fica_fora_da_barreira(request, view_func):
            return None
        if tem_acesso_ao_painel(request.user):
            return None
        return render(request, "sem_acesso.html", status=403)

    @staticmethod
    def _view_fica_fora_da_barreira(
        request: HttpRequest, view_func: Callable[..., HttpResponse]
    ) -> bool:
        # Não barra: quem não está logado, as telas de login/sair e o /admin/
        if not request.user.is_authenticated:
            return True
        if getattr(view_func, "login_required", True) is False:
            return True
        resolvido = request.resolver_match
        return bool(resolvido and resolvido.app_name == "admin")
