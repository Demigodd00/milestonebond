"""Cache GenVM v0.3.0-rc7 runners for genlayer-test 0.29.2 direct tests.

The official release calls this bundle genvm-runners-all.tar.xz; gltest still
expects the older genvm-universal-<version>.tar.xz cache filename.
"""
import hashlib
import os
import tempfile
import urllib.request
from pathlib import Path

VERSION = "v0.3.0-rc7"
EXPECTED_SHA256 = "e218a1854214681560351051f76fe2b878545cf3409455ef372d57014a88ca67"
URL = f"https://github.com/genlayerlabs/genvm/releases/download/{VERSION}/genvm-runners-all.tar.xz"
CACHE = Path.home() / ".cache" / "gltest-direct"
TARGET = CACHE / f"genvm-universal-{VERSION}.tar.xz"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    if TARGET.exists() and sha256(TARGET) == EXPECTED_SHA256:
        print(f"Verified cached GenVM bundle: {VERSION}")
        return
    request = urllib.request.Request(URL, headers={"User-Agent": "MilestoneBond-CI/1.0"})
    descriptor, name = tempfile.mkstemp(prefix="genvm-runners-", suffix=".part", dir=CACHE)
    os.close(descriptor)
    temporary = Path(name)
    try:
        with urllib.request.urlopen(request, timeout=300) as response, temporary.open("wb") as output:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                output.write(chunk)
        actual = sha256(temporary)
        if actual != EXPECTED_SHA256:
            raise RuntimeError(f"GenVM runner checksum mismatch: {actual}")
        os.replace(temporary, TARGET)
        print(f"Downloaded and verified GenVM bundle: {VERSION}")
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
