"""Queued checks of owner-maintained source URLs, with private-network blocking."""
import ipaddress
import socket
import urllib.request
import urllib.error
from urllib.parse import urlsplit
from django.utils import timezone
from .models import Question
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def check(url):
    if not url: return 'Missing URL'
    try:
        parsed=urlsplit(url)
        if parsed.scheme not in ('https','http') or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None,80,443): return 'Unsupported URL'
        addresses=socket.getaddrinfo(parsed.hostname,parsed.port or (443 if parsed.scheme=='https' else 80),type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses): return 'Private/non-public address blocked'
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        with opener.open(urllib.request.Request(url,method='HEAD',headers={'User-Agent':'RERevi-LinkCheck/1.0'}),timeout=4) as response: return 'HTTP '+str(response.status)
    except urllib.error.HTTPError as error:
        if error.code in (301,302,303,307,308): return f'HTTP {error.code}: redirects; review destination manually'
        if error.code in (403,405,429): return f'HTTP {error.code}: automated check blocked; review manually'
        return 'HTTP '+str(error.code)
    except Exception: return 'Could not reach source; review manually'

def check_pending():
    count=0
    for obj in Question.objects.filter(data__link_check_requested=True)[:5]:
        obj.data['link_checks']={'checked_at':timezone.now().isoformat(),'source':check(obj.source_url),'mark_scheme':check(obj.mark_scheme_url)}
        obj.data['link_check_requested']=False;obj.save(update_fields=['data']);count+=1
    return count
