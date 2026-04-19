import urllib.request

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Do not redirect

opener = urllib.request.build_opener(NoRedirectHandler())
urllib.request.install_opener(opener)
