from pathlib import Path

from setuptools import find_packages, setup

here = Path(__file__).resolve().parent
README = (here / "README.md").read_text(encoding="utf-8")
VERSION = (here / "VERSION").read_text(encoding="utf-8").strip()

excluded_packages = ["docs", "tests", "tests.*"]

setup(
    name="VivadoPyTcl",
    version=VERSION,
    description="pyvtcl is a python wrapper for vivado tcl process, you can run tcl cmd directly in python though string and get the result.",
    long_description=README,
    author="odjvnrij",
    author_email="odjvnrij72@outlook.com",
    url="https://github.com/odjvnrij/VivadoPyTcl",
    project_urls={
        "Bug Tracker": "https://github.com/odjvnrij/faker/issues",
        "Source Code": "https://github.com/odjvnrij/VivadoPyTcl",
    },
    license="APACHE LICENSE, VERSION 2.0",
    packages=find_packages(where='.', exclude=(), include=('*',)),
    python_requires=">=3.8",
    install_requires=[],
)
