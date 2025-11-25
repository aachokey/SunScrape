"""Setup configuration for SunScrape."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name='SunScrape',
    version='0.2.0',
    author="Aric Chokey",
    author_email="achokey21@gmail.com",
    description="A python library to scrape campaign finance records from the Florida Secretary of State.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SunSentinel/SunScrape",
    packages=find_packages(),
    install_requires=[
        "beautifulsoup4>=4.9.0",
        "requests>=2.25.0",
    ],
    python_requires=">=3.7",
    license="MIT",
    keywords=["campaign finance", "florida", "politics", "money", "scraping"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
