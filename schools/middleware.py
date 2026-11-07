class AuditMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated and request.method in ['POST'] and '/admin/' not in request.path:
            from .utils import log_action
            log_action(request, f"{request.method} {request.path}", f"User {request.user.username}")
        return response