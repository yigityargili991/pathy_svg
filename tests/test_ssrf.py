import pytest
from pathy_svg.document import SVGDocument

def test_from_url_blocks_internal_ips():
    with pytest.raises(ValueError, match="URL points to a non-global IP address"):
        SVGDocument.from_url("http://127.0.0.1:8000/test.svg")

    with pytest.raises(ValueError, match="URL points to a non-global IP address"):
        SVGDocument.from_url("http://localhost:8000/test.svg")

    with pytest.raises(ValueError, match="URL points to a non-global IP address"):
        SVGDocument.from_url("http://169.254.169.254/latest/meta-data/")

def test_from_url_invalid_hostname():
    with pytest.raises(ValueError, match="Invalid URL hostname"):
        SVGDocument.from_url("http:///")
