from __future__ import annotations

import platform
import sys

from echotype.services.diagnostics import safe_detail


def ok(label: str, detail: str = "") -> None:
    detail = safe_detail(detail)
    suffix = f"  {detail}" if detail else ""
    print(f"  [ok]   {label:<34}{suffix}")


def warn(label: str, detail: str = "") -> None:
    detail = safe_detail(detail)
    suffix = f"  {detail}" if detail else ""
    print(f"  [warn] {label:<34}{suffix}")


def fail(label: str, detail: str = "") -> None:
    detail = safe_detail(detail)
    suffix = f"  {detail}" if detail else ""
    print(f"  [FAIL] {label:<34}{suffix}")


def main() -> int:
    print("\nEchoType V2 verification\n")
    failures = 0

    version = sys.version_info[:2]
    if version in {(3, 11), (3, 12)}:
        ok("Python version", platform.python_version())
    else:
        fail("Python version", f"{platform.python_version()} (need 3.11 or 3.12)")
        failures += 1

    try:
        import echotype

        ok("EchoType package", echotype.__version__)
    except Exception as exc:
        fail("EchoType package", str(exc))
        failures += 1

    for module_name in (
        "PySide6",
        "numpy",
        "scipy",
        "sounddevice",
        "noisereduce",
        "webrtcvad",
        "pynput",
        "transformers",
        "huggingface_hub",
        "sentencepiece",
    ):
        try:
            module = __import__(module_name)
            detail = str(getattr(module, "__version__", "imported"))
            ok(module_name, detail)
        except Exception as exc:
            fail(module_name, str(exc))
            failures += 1

    try:
        import torch

        ok("PyTorch", torch.__version__)
        if torch.cuda.is_available() and torch.cuda.device_count() > 0:
            ok("CUDA", torch.cuda.get_device_name(0))
        else:
            warn("CUDA", "not available; EchoType will use CPU")
    except Exception as exc:
        fail("PyTorch", str(exc))
        failures += 1

    if sys.platform == "win32":
        try:
            import win32gui  # noqa: F401

            ok("Windows integration", "pywin32 available")
        except Exception as exc:
            fail("Windows integration", str(exc))
            failures += 1
    else:
        warn("Windows integration", f"running on {sys.platform}; paste-back is Windows-first")

    try:
        from echotype.core.audio import AudioEngine
        from echotype.services.model_revision import immutable_revision
        from echotype.services.settings import Settings

        devices = AudioEngine.list_devices()
        if devices:
            ok("Microphone inputs", f"{len(devices)} detected")
            for index, name in devices[:5]:
                print(f"           - {index}: {name}")
        else:
            warn("Microphone inputs", "none detected")

        settings = Settings()
        for label, key in (
            ("Pinned mirror revision", "model_revision"),
            ("Pinned upstream revision", "upstream_model_revision"),
        ):
            revision = immutable_revision(settings.get(key))
            if revision:
                ok(label, revision[:12])
            else:
                warn(label, "will be resolved before any remote model code executes")
    except Exception as exc:
        warn("Runtime diagnostics", str(exc))

    print()
    if failures:
        print(f"Verification finished with {failures} failure(s).")
        return 1
    print("Verification passed. Hardware/model transcription still needs a live dictation test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
