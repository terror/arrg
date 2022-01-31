import os
from setuptools import setup, find_packages

def read(fname):
  return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
  name="arrg",
  version="0.0.0",
  author="Liam Scalzulli",
  author_email="liam@scalzulli.com",
  description=("A library for creating ergonomic command-line applications"),
  long_description_content_type="text/markdown",
  license="CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
  keywords="",
  url="http://packages.python.org/arrg",
  project_urls={"Source Code": "https://github.com/terror/arrg"},
  packages=find_packages(),
  long_description=read("README.md"),
  classifiers=[
    "Development Status :: 3 - Alpha",
    "Topic :: library",
    "License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication"
  ],
  install_requires=[],
  python_requires=">= 3.9",
)
