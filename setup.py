"""Setup script for IncludeGuard"""
from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding='utf-8')

setup(
    name="includeguard",
    version="2.0.0",
    author="Harsh",
    author_email="you@example.com",
    description="A C++ include dependency analyzer with build cost estimation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/includeguard",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/includeguard/issues",
        "Documentation": "https://includeguard.readthedocs.io",
        "Source Code": "https://github.com/yourusername/includeguard",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0",
        "rich>=10.0",
        "networkx>=2.6",
        "plotly>=5.0",
        "pandas>=1.3",
        "pydot>=1.4",
        "flask>=2.0.0",
        "flask-cors>=3.0.0",
        "requests>=2.26.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.12.0",
            "pytest-timeout>=1.4.0",
            "black>=21.0",
            "flake8>=3.9.0",
            "mypy>=0.910",
            "bandit>=1.7.0",
            "safety>=1.10.0",
            "sphinx>=4.0",
            "sphinx-rtd-theme>=1.0",
            "sphinx-autodoc-typehints>=1.12.0",
            "psutil>=5.8.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "includeguard=includeguard.cli:main",
        ],
    },
)
