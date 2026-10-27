"""Stable root aliases for browser home-screen icon requests."""
from django.conf import settings
from django.http import FileResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_safe

@require_safe
@cache_control(public=True,max_age=604800)
def apple_touch_icon(request,size=None):
    filename='apple-touch-icon-240x240.png' if size=='240x240' else 'apple-touch-icon-180x180.png'
    from .site_scope import site_for_request
    site=site_for_request(request)
    folder=''
    response=FileResponse((settings.BASE_DIR/'static'/folder/filename).open('rb'),content_type='image/png')
    response['X-Content-Type-Options']='nosniff'
    return response
