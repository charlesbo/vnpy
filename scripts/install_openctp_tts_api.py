"""Install matching OpenCTP TTS CTPAPI shared libraries into vnpy_ctp."""

import argparse
import importlib.metadata
import platform
import re
import shutil
import tempfile
import zipfile
from pathlib import Path


LIBRARIES = ("libthostmduserapi_se.so", "libthosttraderapi_se.so")


def parse_ctp_version(value: str) -> str:
    """Return the three-part CTP API version from an SDK/package label."""
    match = re.search(r"(?<!\d)(\d+\.\d+\.\d+)(?:\.\d+)?", value)
    if not match:
        raise ValueError(f"Could not read a CTP API version from {value!r}")
    return match.group(1)


def locate_sdk_libraries(archive: zipfile.ZipFile) -> tuple[str, dict[str, bytes]]:
    """Locate the x86_64 Linux API libraries and the SDK's CTP version."""
    names = archive.namelist()
    candidates = [name for name in names if "/lin64/" in name]
    versions = {
        parse_ctp_version(match.group(1))
        for name in candidates
        if (match := re.search(r"(?:^|/)(?:tts|TTS)[_-]?(\d+\.\d+\.\d+)(?:/|$)", name))
    }
    if len(versions) != 1:
        raise ValueError(f"Expected one TTS CTP API version in archive, found {sorted(versions)}")

    libraries: dict[str, bytes] = {}
    for library in LIBRARIES:
        matches = [name for name in candidates if name.endswith(f"/lin64/{library.removeprefix('lib')}")]
        if len(matches) != 1:
            raise ValueError(f"Expected one Linux {library.removeprefix('lib')} in archive, found {matches}")
        data = archive.read(matches[0])
        if not data.startswith(b"\x7fELF") or b"openctp-tts v" not in data:
            raise ValueError(f"{matches[0]} is not a recognized OpenCTP TTS ELF library")
        libraries[library] = data
    return versions.pop(), libraries


def install_libraries(archive_path: Path, api_dir: Path, installed_version: str | None = None) -> None:
    """Back up original CTP libraries and atomically install matching TTS files."""
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "amd64"}:
        raise RuntimeError("This helper currently installs only x86_64 Linux TTS libraries")

    if installed_version is None:
        installed_version = importlib.metadata.version("vnpy_ctp")
    installed_api_version = parse_ctp_version(installed_version)
    with zipfile.ZipFile(archive_path) as archive:
        sdk_version, libraries = locate_sdk_libraries(archive)
    if sdk_version != installed_api_version:
        raise RuntimeError(
            f"TTS API {sdk_version} does not match installed vnpy_ctp API {installed_api_version}; "
            "install the exact matching TTS SDK instead."
        )

    api_dir = api_dir.resolve()
    if not api_dir.is_dir():
        raise FileNotFoundError(f"vnpy_ctp API directory not found: {api_dir}")

    staged: dict[str, Path] = {}
    with tempfile.TemporaryDirectory(dir=api_dir) as temp_dir:
        for library, data in libraries.items():
            target = api_dir / library
            if not target.is_file():
                raise FileNotFoundError(f"Expected installed CTP library not found: {target}")
            backup = api_dir / f"{library}.official.bak"
            if not backup.exists():
                shutil.copy2(target, backup)
            staged_path = Path(temp_dir) / library
            staged_path.write_bytes(data)
            shutil.copystat(target, staged_path)
            staged[library] = staged_path

        for library, staged_path in staged.items():
            staged_path.replace(api_dir / library)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="OpenCTP TTS SDK zip matching installed vnpy_ctp")
    parser.add_argument(
        "--api-dir",
        type=Path,
        default=None,
        help="vnpy_ctp/api directory (defaults to the active Python environment)",
    )
    args = parser.parse_args()
    if args.api_dir is None:
        import vnpy_ctp.api

        api_dir = Path(vnpy_ctp.api.__file__).parent
    else:
        api_dir = args.api_dir

    install_libraries(args.archive, api_dir)
    print(f"Installed OpenCTP TTS {parse_ctp_version(args.archive.name)} libraries in {api_dir}")
    print("Original CTP libraries were preserved with the .official.bak suffix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
