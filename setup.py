from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
import subprocess
import sys

class BuildPyCommand(_build_py):
    """Custom build command that runs nexuscore_build.py first."""
    def run(self):
        # Run the custom nexuscore_build.py
        subprocess.check_call([sys.executable, 'nexuscore_build.py'])
        # Then run the normal build
        super().run()

class BDistWheelCommand(_bdist_wheel):
    """Mark wheel as non-pure (platform-specific) since we ship compiled extensions."""
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False

setup(
    cmdclass={
        'build_py': BuildPyCommand,
        'bdist_wheel': BDistWheelCommand,
    },
)
