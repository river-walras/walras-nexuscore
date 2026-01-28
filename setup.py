from setuptools import setup, Extension
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.build_ext import build_ext as _build_ext
import subprocess
import sys


class BuildPyCommand(_build_py):
    """Custom build command that runs nexuscore_build.py first."""
    def run(self):
        subprocess.check_call([sys.executable, 'nexuscore_build.py'])
        super().run()


class NoopBuildExt(_build_ext):
    """Skip build_ext since extensions are already compiled by nexuscore_build.py."""
    def build_extensions(self):
        pass


# Declare a sentinel ext_module so setuptools marks the wheel as platlib
# (platform-specific). The actual compilation is handled by nexuscore_build.py
# via the BuildPyCommand above; NoopBuildExt ensures setuptools doesn't try to
# compile this dummy entry itself.
setup(
    ext_modules=[
        Extension("nexuscore._sentinel", sources=[]),
    ],
    cmdclass={
        'build_py': BuildPyCommand,
        'build_ext': NoopBuildExt,
    },
)
