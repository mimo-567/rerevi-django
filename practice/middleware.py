from django.conf import settings
from django.shortcuts import redirect

class AccessMiddleware:
    def __init__(self, get_response): self.get_response=get_response
    def __call__(self, request):
        allowed = request.path.startswith(('/access/','/admin/','/static/','/healthz/','/s/'))
        if not settings.PUBLIC_ACCESS and not allowed and not request.user.is_staff and not request.session.get('practice_access'):
            return redirect('access')
        return self.get_response(request)

class HeadersMiddleware:
    def __init__(self, get_response): self.get_response=get_response
    def __call__(self, request):
        response=self.get_response(request)
        response['Referrer-Policy']='same-origin'
        response['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        response['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        if request.path.startswith(('/s/','/api/shares/')):
            response['Referrer-Policy']='no-referrer'
            response['X-Robots-Tag']='noindex, nofollow, noarchive'
        if request.path.startswith(('/resources','/english/documents/','/documents/')):
            response['Content-Security-Policy']=response['Content-Security-Policy'].replace("frame-ancestors 'none'", "frame-ancestors 'self'")
        if request.path.startswith('/admin/'):
            # Django admin's own widgets use inline styles.
            response['Content-Security-Policy']=response['Content-Security-Policy'].replace("style-src 'self'", "style-src 'self' 'unsafe-inline'")
        if not request.path.startswith('/static/'):
            response['Cache-Control']='private, no-store'
        return response
