from setuptools import setup, find_packages

setup(
    name="fntx-cli",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click",
        "rich",
    ],
    entry_points={
        "console_scripts": [
            "fntx=cli.main:cli",
        ],
    },
    python_requires=">=3.8",
)
