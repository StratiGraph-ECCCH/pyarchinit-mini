from pyarchinit_mini.web_interface.media_serve import serve_decision


def test_cloudinary_redirects_stripping_thumb():
    kind, val = serve_decision("cloudinary://f/2446_x_thumb.png")
    assert kind == "redirect" and val == "https://res.cloudinary.com/dkioeufik/image/upload/f/2446_x.png"


def test_http_redirects():
    assert serve_decision("https://h/x.png") == ("redirect", "https://h/x.png")


def test_s3_is_proxy():
    kind, _ = serve_decision("s3://bucket/x.png"); assert kind == "proxy"


def test_unibo_is_proxy():
    kind, _ = serve_decision("unibo://P/f/x.png"); assert kind == "proxy"


def test_local_is_file():
    kind, _ = serve_decision("/data/x.png"); assert kind == "file"


def test_sftp_is_forbidden():
    """sftp:// is a recognized remote scheme (path_resolver.REMOTE_SCHEMES)
    but not in serve_decision's proxy list, so it must be rejected rather
    than silently 501'd or served as a local file."""
    kind, _ = serve_decision("sftp://host/x.png"); assert kind == "forbidden"
