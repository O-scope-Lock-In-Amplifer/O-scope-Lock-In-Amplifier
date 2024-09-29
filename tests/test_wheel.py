"""Test that the built wheel includes all the files in the package."""

import os
from pathlib import Path
import shutil
import sys
from typing import Optional
import unittest
from zipfile import ZipFile


class TestUtil(unittest.TestCase):
    """Test that the built wheel includes all the files in the package."""

    def test_wheel_include(self) -> None:
        """Test that the built wheel includes all the files in the package."""
        self._test_wheel_include("o_scope_lock_in_amplifier")

    def setUp(self) -> None:
        """Create the wheel files for subsequent tests."""
        self.proj_dir = Path(__file__).parent.parent.absolute()
        self.dist_dir = self.proj_dir / "dist"

        # Clean "dist" directory.
        try:
            shutil.rmtree(self.dist_dir)
        except FileNotFoundError:
            # Already clean!
            pass

        # Build wheel.
        if (sys.executable is None) or (len(sys.executable) < 1):
            raise RuntimeError("Unknown interpreter!")
        interpeter = sys.executable
        os.chdir(self.proj_dir)
        os.system(f"\"{interpeter}\" -m build --wheel")

    def _test_wheel_include(
        self, mod_dir_name: str, mod_whl_name: Optional[str] = None
    ) -> None:
        """Test that the built wheel includes all the files in a package."""
        if mod_whl_name is None:
            mod_whl_name = mod_dir_name
        mod_dir = self.proj_dir / mod_dir_name

        # Get wheel file and ensure there's only one.
        wheel_files = list(self.dist_dir.glob(f"{mod_whl_name}*.whl"))
        self.assertEqual(
            len(wheel_files),
            1,
            f"{len(wheel_files)} wheels detected for {mod_whl_name} (expected 1)!",
        )
        wheel_file = wheel_files[0]
        zip_dir_filelist = list()

        # Get list of files in wheel (which is a ZIP file).
        with ZipFile(wheel_file, "r") as zipf:
            for f in zipf.namelist():
                if f.startswith(f"{mod_dir_name}/") and "__pycache__" not in f:
                    # Find files in the package dir in the wheel and strip the
                    # package prefix.
                    # Zip module uses foward slashes regardless of the os.sep.
                    # There's probably a smarter way to construct this Path...
                    zip_dir_filelist.append(Path(f[len(f"{mod_dir_name}/") :]))

        real_dir_filelist = [
            # Strip full path info off, so it matches zip listings
            f.relative_to(mod_dir)
            # Glob for all files in the module directory
            for f in mod_dir.glob("**/*")
            # Remove __pycache__ directories and pure directories
            if "__pycache__" not in str(f) and not f.is_dir()
        ]

        # Test that sequence first contains the same elements as second,
        # regardless of their order.
        self.maxDiff = 1000000
        self.assertCountEqual(
            zip_dir_filelist,
            real_dir_filelist,
            "Wheel is not in sync with source directory.",
        )
