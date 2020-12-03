import pathlib

from setuptools import setup

directory = pathlib.Path(__file__).parent
readme = directory.joinpath("README.md").read_text(encoding="utf-8")

setup(
    use_scm_version=True,
    long_description=readme,
    long_description_content_type="text/markdown",
)
