from setuptools import setup, find_packages

setup(
    name="quantum_stego_agent",
    version="0.1.0",
    description="Steganographic Memory Execution System with Autonomous AI Agents",
    author="JMKstudio",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.21.0",
        "cryptography>=3.4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "stego-terminal=src.terminal.cli:main",
        ],
    },
)
