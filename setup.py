from setuptools import setup, find_packages

setup(
    name="CRRScraper",
    version="0.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    author="LKX",
    install_requires=[
        # List your dependencies here
    ],
)