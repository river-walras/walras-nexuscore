from setuptools import setup, Distribution
from setuptools.command.build_py import build_py as _build_py
import subprocess
import sys


class BinaryDistribution(Distribution):
    """Force setuptools to treat this as a platform-specific (platlib) package."""
    def has_ext_modules(self):
        return True


class BuildPyCommand(_build_py):
    """Custom build command that runs nexuscore_build.py first."""
    def run(self):
        subprocess.check_call([sys.executable, 'nexuscore_build.py'])
        super().run()


setup(
    distclass=BinaryDistribution,
    cmdclass={
        'build_py': BuildPyCommand,
    },
)
