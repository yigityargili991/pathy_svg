## 2024-05-18 - [SSRF Protection added to `SVGDocument.from_url`]
**Vulnerability:** Server-Side Request Forgery (SSRF). `urllib.request.urlopen` was being used directly, allowing the application to fetch arbitrary URLs such as `http://127.0.0.1` or `http://169.254.169.254/latest/meta-data/`.
**Learning:** External URL fetching must be restricted to safe IP addresses.
**Prevention:** `SVGDocument.from_url` now restricts IP addresses by resolving hostnames and blocking access to private, loopback, link-local, unspecified, multicast, and reserved IP ranges. It also uses a custom `_NoRedirectHandler` to prevent bypasses via HTTP redirects. Note: the defense is slightly susceptible to TOCTOU DNS rebinding since standard `urllib` still fetches via the original URL after checking the IP.
