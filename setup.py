import os
import platform
from pathlib import Path

from Cython.Build import cythonize
from setuptools import Extension
from setuptools import setup


IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

extra_compile_args = []
extra_link_args = []
if not IS_WINDOWS:
    extra_compile_args += ["-O2", "-Wno-unreachable-code"]
if IS_LINUX:
    # Strip symbols at link time to keep the shared objects small.
    extra_link_args += ["-Wl,-s"]

VENDOR_SECP256K1 = Path("vendor/secp256k1")
SECP256K1_EXTENSION = "nexuscore.common.secp256k1"

if not (VENDOR_SECP256K1 / "src" / "secp256k1.c").exists():
    raise SystemExit(
        f"missing vendored libsecp256k1 sources under {VENDOR_SECP256K1}. If this "
        "is a git checkout the tree is incomplete; if this is an sdist it was "
        "built wrong (see MANIFEST.in)."
    )


def _build_extension(pyx: Path) -> Extension:
    name = str(pyx.with_suffix("")).replace(os.sep, ".")

    # common.secp256k1 links vendored libsecp256k1 rather than a system library,
    # so it needs its own sources and defines instead of the bare .pyx build the
    # other extensions get. Upstream ships the precomputed ecmult tables as .c, so
    # these three translation units are the whole library -- no autotools/cmake and
    # no codegen. ENABLE_MODULE_RECOVERY is what pulls in
    # secp256k1_ecdsa_sign_recoverable; everything else is deliberately left to
    # upstream's in-header defaults (ECMULT_WINDOW_SIZE, COMB_BLOCKS/COMB_TEETH),
    # because the vendored precomputed tables were generated for exactly those
    # values and overriding them would silently disagree with the shipped tables.
    if name == SECP256K1_EXTENSION:
        return Extension(
            name,
            [
                str(pyx),
                *(
                    str(VENDOR_SECP256K1 / "src" / source)
                    for source in (
                        "secp256k1.c",
                        "precomputed_ecmult.c",
                        "precomputed_ecmult_gen.c",
                    )
                ),
            ],
            include_dirs=[
                str(VENDOR_SECP256K1 / "include"),
                str(VENDOR_SECP256K1),
                str(VENDOR_SECP256K1 / "src"),
            ],
            define_macros=[("ENABLE_MODULE_RECOVERY", "1")],
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
        )

    return Extension(
        name,
        [str(pyx)],
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    )


extensions = [_build_extension(pyx) for pyx in sorted(Path("nexuscore").rglob("*.pyx"))]

setup(
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": "3",
            "cdivision": True,
            "nonecheck": True,
            "embedsignature": True,
        },
        nthreads=os.cpu_count() or 1,
    ),
)
