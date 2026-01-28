from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
import subprocess
import sys

class BuildPyCommand(_build_py):
    """Custom build command that runs nexuscore_build.py first."""
    def run(self):
        # Run the custom nexuscore_build.py
        subprocess.check_call([sys.executable, 'nexuscore_build.py'])
        # Then run the normal build
        super().run()

setup(
    cmdclass={
        'build_py': BuildPyCommand,
    },
)
