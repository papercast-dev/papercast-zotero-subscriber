from pathlib import Path
import subprocess
import shutil
import pkg_resources
from setuptools import find_packages


def find_papercast() -> str:
    package = pkg_resources.get_distribution("papercast")
    return package.location


def generate_stubs(plugin_folder, plugin_file, output_dir):
    cmd = [
        "stubgen",
        "-o",
        str(output_dir / f"{plugin_folder}_{plugin_file}"),
        "--no-import",
        "--export-less",
        "-m",
        f"{plugin_folder}.{plugin_file}",
    ]
    print(" ".join(cmd))
    subprocess.run(
        cmd,
        check=True,
    )


def move_stubs(output_dir):
    for stub_folder in output_dir.glob("*"):
        if stub_folder.is_dir():
            folder_files = list(stub_folder.glob("**/*.pyi"))
            if not len(folder_files) == 1:
                raise ValueError(
                    f"Expected one file in {stub_folder}, found {folder_files}"
                )
            file = folder_files[0]
            file.rename(output_dir / f"{stub_folder.name}.pyi")
            shutil.rmtree(stub_folder)

            # append "from .{stub_folder.name} import *" to output_dir / __init__.pyi
            # with open(output_dir / "__init__.pyi", "a") as f:
            # f.write(f"\nfrom .{stub_folder.name} import *")
            # same as above, but check if it's already there
            if not (output_dir / "__init__.pyi").exists():
                with open(output_dir / "__init__.pyi", "w") as f:
                    f.write(f"from .{stub_folder.name} import *")
            else:
                with open(output_dir / "__init__.pyi", "r") as f:
                    if f"from .{stub_folder.name} import *" not in f.read():
                        with open(output_dir / "__init__.pyi", "a") as f:
                            f.write(f"\nfrom .{stub_folder.name} import *")
                    else:
                        print(
                            f"Skipping {stub_folder.name} import in __init__.pyi, already exists"
                        )


if __name__ == "__main__":
    package_dirs = find_packages()

    papercast_dir = find_papercast() + "/papercast"

    for plugin_folder in package_dirs:
        plugin_files = Path(plugin_folder).glob("*.py")
        for plugin_file in plugin_files:
            if plugin_file.stem in ["subscribers", "processors", "types", "publishers"]:
                output_dir = Path(papercast_dir) / plugin_file.stem / "stubs"
                print(f"Generating stubs for {plugin_file} in {output_dir}...")
                generate_stubs(plugin_folder, plugin_file.stem, output_dir)
                move_stubs(output_dir)
