from setuptools import setup, find_packages

setup(
    name="pychronicle",
    version="1.0.0",
    description="AST-Powered Time-Travel Debugger for Python",
    author="Krishna Potdar",
    packages=find_packages(),
    py_modules=["ast_variable_parser", "storage", "tracer", "ui", "cli"],
    install_requires=[
        "click>=8.0.0",
        "rich>=13.0.0",
        "textual>=0.50.0",
    ],
    entry_points={
        "console_scripts": [
            "pychronicle = cli:main",
        ],
    },
    python_requires=">=3.9",
)
