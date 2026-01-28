#!/usr/bin/env python3

import itertools
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import numpy as np
from Cython.Build import build_ext
from Cython.Build import cythonize
from Cython.Compiler import Options
from setuptools import Distribution
from setuptools import Extension


# Platform constants
IS_LINUX = platform.system() == "Linux"
IS_MACOS = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"
IS_ARM64 = platform.machine() in ("arm64", "aarch64")

BUILD_MODE = os.getenv("BUILD_MODE", "release")
os.environ.setdefault("RUSTUP_TOOLCHAIN", "1.93.0")
os.environ.setdefault("PYO3_PYTHON", sys.executable)

if IS_MACOS and IS_ARM64:
    os.environ["CFLAGS"] = f"{os.environ.get('CFLAGS', '')} -arch arm64"
    os.environ["LDFLAGS"] = f"{os.environ.get('LDFLAGS', '')} -arch arm64 -w"

if IS_LINUX:
    # Prefer clang if available; fall back to system default (gcc) on manylinux.
    if shutil.which("clang") and shutil.which("clang++"):
        os.environ.setdefault("CC", "clang")
        os.environ.setdefault("CXX", "clang++")
        os.environ["LDSHARED"] = "clang -shared"

if IS_WINDOWS:
    RUST_LIB_PFX = ""
    RUST_STATIC_LIB_EXT = "lib"
    RUST_DYLIB_EXT = "dll"
elif IS_MACOS:
    RUST_LIB_PFX = "lib"
    RUST_STATIC_LIB_EXT = "a"
    RUST_DYLIB_EXT = "dylib"
else:
    RUST_LIB_PFX = "lib"
    RUST_STATIC_LIB_EXT = "a"
    RUST_DYLIB_EXT = "so"

CARGO_TARGET_DIR = os.environ.get("CARGO_TARGET_DIR", Path.cwd() / "target")
profile_dir = "release" if BUILD_MODE == "release" else "debug"
CARGO_TARGET_DIR = Path(CARGO_TARGET_DIR) / profile_dir

RUST_INCLUDES = ["nexuscore/core/includes"]
RUST_LIB_PATHS = [
    CARGO_TARGET_DIR / f"{RUST_LIB_PFX}nautilus_common.{RUST_STATIC_LIB_EXT}",
    CARGO_TARGET_DIR / f"{RUST_LIB_PFX}nautilus_core.{RUST_STATIC_LIB_EXT}",
    CARGO_TARGET_DIR / f"{RUST_LIB_PFX}nautilus_model.{RUST_STATIC_LIB_EXT}",
]
RUST_LIBS = [str(path) for path in RUST_LIB_PATHS]

################################################################################
#  RUST BUILD
################################################################################

def _build_rust_libs():
    print("Compiling Rust static libraries...")
    build_options = ["--release"] if BUILD_MODE == "release" else []

    # Build static libraries with FFI
    cmd_args = [
        "cargo", "build", "--lib",
        "-p", "nautilus-core",
        "-p", "nautilus-common",
        "-p", "nautilus-model",
        *build_options,
        "--no-default-features",
        "--features", "ffi,python",
    ]
    print(" ".join(cmd_args))
    pyo3_env = os.environ.copy()
    # Avoid linking libpython when building Rust static libs; the final
    # Python extension will resolve symbols at link/load time.
    pyo3_env.setdefault("PYO3_NO_PYTHON", "1")
    subprocess.run(cmd_args, check=True, env=pyo3_env)

    # Build PyO3 cdylib
    pyo3_cmd = [
        "cargo", "build", "--lib",
        "-p", "nexuscore-pyo3",
        *build_options,
        "--features", "extension-module",
    ]
    print(" ".join(pyo3_cmd))
    pyo3_env = os.environ.copy()
    if IS_MACOS:
        extra = "-C link-arg=-undefined -C link-arg=dynamic_lookup"
        pyo3_env["RUSTFLAGS"] = f"{pyo3_env.get('RUSTFLAGS', '')} {extra}".strip()
    subprocess.run(pyo3_cmd, check=True, env=pyo3_env)


def _copy_rust_dylibs():
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    src = Path(CARGO_TARGET_DIR) / f"{RUST_LIB_PFX}nexuscore_pyo3.{RUST_DYLIB_EXT}"
    dst = Path("nexuscore") / f"_nexuscore_pyo3{ext_suffix}"
    shutil.copyfile(src=src, dst=dst)
    print(f"Copied {src} to {dst}")


################################################################################
#  CYTHON BUILD
################################################################################

Options.docstrings = True
Options.fast_fail = True

CYTHON_COMPILER_DIRECTIVES = {
    "language_level": "3",
    "cdivision": True,
    "nonecheck": True,
    "embedsignature": True,
    "profile": False,
    "linetrace": False,
    "warn.maybe_uninitialized": True,
}


def _build_extensions():
    define_macros = [("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")]
    extra_compile_args = []
    extra_link_args = list(RUST_LIBS)

    if not IS_WINDOWS:
        extra_compile_args.append("-Wno-unreachable-code")
        if BUILD_MODE == "release":
            extra_compile_args.append("-O2")
            extra_compile_args.append("-pipe")

    print("Creating C extension modules...")
    return [
        Extension(
            name=str(pyx.relative_to(".")).replace(os.path.sep, ".")[:-4],
            sources=[str(pyx)],
            include_dirs=[np.get_include(), *RUST_INCLUDES],
            define_macros=define_macros,
            language="c",
            extra_link_args=extra_link_args,
            extra_compile_args=extra_compile_args,
        )
        for pyx in Path("nexuscore").rglob("*.pyx")
    ]


def _build_distribution(extensions):
    nthreads = os.cpu_count() or 1
    distribution = Distribution(
        {
            "name": "nexuscore",
            "ext_modules": cythonize(
                module_list=extensions,
                compiler_directives=CYTHON_COMPILER_DIRECTIVES,
                nthreads=nthreads,
                build_dir="build/optimized",
            ),
            "zip_safe": False,
        },
    )
    return distribution


def _copy_build_dir_to_project(cmd):
    for output in cmd.get_outputs():
        relative_extension = Path(output).relative_to(cmd.build_lib)
        if not Path(output).exists():
            continue
        shutil.copyfile(output, relative_extension)
        mode = relative_extension.stat().st_mode
        mode |= (mode & 0o444) >> 2
        relative_extension.chmod(mode)
    print("Copied all compiled dynamic library files into source")


def _strip_unneeded_symbols():
    if IS_WINDOWS:
        return
    print("Stripping unneeded symbols from binaries...")
    for so in Path("nexuscore").rglob("*.so"):
        if IS_MACOS:
            subprocess.run(["strip", "-x", so], check=True, capture_output=True)
        else:
            subprocess.run(
                ["strip", "--strip-all", "-R", ".comment", "-R", ".note", so],
                check=True,
                capture_output=True,
            )


def build():
    _build_rust_libs()
    _copy_rust_dylibs()

    extensions = _build_extensions()
    distribution = _build_distribution(extensions)

    print("Compiling C extension modules...")
    cmd = build_ext(distribution)
    cmd.parallel = os.cpu_count()
    cmd.ensure_finalized()
    cmd.run()

    _copy_build_dir_to_project(cmd)

    if BUILD_MODE == "release" and not IS_WINDOWS:
        _strip_unneeded_symbols()


if __name__ == "__main__":
    print(f"System: {platform.system()} {platform.machine()}")
    print(f"Python: {platform.python_version()} ({sys.executable})")
    print(f"NumPy:  {np.__version__}")
    print(f"BUILD_MODE={BUILD_MODE}")
    print("\nStarting build...")
    build()
    print("\033[32mBuild completed\033[0m")
