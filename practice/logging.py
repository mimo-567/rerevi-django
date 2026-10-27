import logging
class OmitShareURLs(logging.Filter):
    def filter(self,record):
        request=getattr(record,'request',None)
        return request is None or not request.path.startswith('/s/')
