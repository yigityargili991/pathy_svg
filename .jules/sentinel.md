## 2024-05-24 - [Centralize Secure XML Parser]
**Vulnerability:** Several places in the codebase parsed XML without disabling entity resolution or network access, leading to potential XXE (XML External Entity) vulnerabilities.
**Learning:** `lxml`'s default parser does not disable entity resolution. All `etree.fromstring` and `etree.parse` calls must explicitly use a secure parser.
**Prevention:** A centralized `get_secure_parser()` function in `_constants.py` was created. All XML parsing must use `parser=get_secure_parser()` to ensure it is secure against XXE.
