from setuptools import find_packages, setup

with open("requirements.txt") as f:
    required = f.read().splitlines()

setup(
    name="anything-db",
    version="0.0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=required,
)
