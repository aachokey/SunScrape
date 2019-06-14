from distutils.core import setup
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='SunScrape',
    version='0.2',
    author="Aric Chokey",
    author_email="achokey21@gmail.com",
    description="A python library to scrape campaign " +
    "finance records from the Florida Secretary of State.",
    long_description=long_description,
    url="https://github.com/SunSentinel/SunScrape",
    packages=setuptools.find_packages(),
    license="MIT",
    keywords=["campaign finance", "florida", "politics", "money"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ]
)
