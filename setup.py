from distutils.core import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='SunScrape',
    version='0.1',
    author="Aric Chokey",
    author_email="achokey21@gmail.com",
    description="A python library to scrape campaign " +
    "finance records from the Florida Secretary of State.",
    long_description=long_description,
    url="https://github.com/SunSentinel/SunScrape",
    license="MIT",
    keywords=["campaign finance", "florida", "politics", "money"]
)
