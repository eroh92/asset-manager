#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

import asset_manager

setup(
    name='asset-manager',
    version=asset_manager.__version__,
    author='Rob Eroh',
    author_email='rob@eroh.me',
    description="Application that manages and minifies your "
                "JavaScript and CSS while also making sprites "
                "from your images.",
    install_requires=['PIL'],
    packages=find_packages(),
    include_package_data=True,
    package_data={
        '': ['bin/*.jar']
    },
    zip_safe=False,
    url='http://github.com/eroh92/asset_manager/',
    classifiers=[
        "Environment :: Web Environment",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
    long_description="",
)
