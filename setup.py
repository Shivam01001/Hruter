from setuptools import setup, find_packages

setup(
    name="hruter",
    version="1.0.0",
    author="Shivam",
    description="Smart Brute Force Tool for Kali Linux",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
        "urllib3>=1.26.0",
    ],
    entry_points={
        "console_scripts": [
            "hruter=hruter:main",
        ],
    },
    python_requires=">=3.7",
)
