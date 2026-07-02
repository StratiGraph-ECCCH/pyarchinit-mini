from pyarchinit_mini.storage.backends.local_backend import LocalBackend

def test_write_read_exists_delete(tmp_path):
    b = LocalBackend(str(tmp_path)); b.connect()
    assert b.write("sub/x.txt", b"hello") is True
    assert b.exists("sub/x.txt") is True
    assert b.read("sub/x.txt") == b"hello"
    assert b.delete("sub/x.txt") is True
    assert b.exists("sub/x.txt") is False

def test_read_missing_returns_none(tmp_path):
    b = LocalBackend(str(tmp_path)); b.connect()
    assert b.read("nope.txt") is None
