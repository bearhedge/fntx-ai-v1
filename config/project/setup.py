from setuptools import setup, find_packages

setup(
    name="fntx-tui",
    version="0.1.0",
    description="FNTX Trading CLI - Professional Options Trading Terminal",
    author="FNTX AI",
    author_email="info@fntx.ai",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "click>=8.0.0",
        "rich>=13.0.0",
        "yfinance>=0.2.0",
        "textual>=0.40.0",
    ],
    entry_points={
        "console_scripts": [
            "fntx=fntx_tui.main:cli",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
