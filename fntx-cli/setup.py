from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fntx-agent",
    version="0.1.0",
    author="FNTX Team",
    author_email="contact@fntx.ai",
    description="The Utopian Machine - Trading Intelligence Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fntx-ai/fntx-agent",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        # Core dependencies from requirements.txt
    ],
    entry_points={
        "console_scripts": [
            "fntx=cli.main:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "fntx_agent": ["config/*.yaml", "config/*.json"],
    },
)