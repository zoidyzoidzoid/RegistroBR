import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='RegistroBR',
    version='0.5',
    author='Code originally by RegistroBR. Modified by William Stewart',
    author_email='zoidbergwill@gmail.com',
    description=('A custom library for contacting the RegistroBR API'),
    license = 'Custom Registro.br License',
    keywords = 'registro.br .com.br domains',
    url = 'https://github.com/zoidbergwill/RegistroBR',
    packages=['RegistroBR'],
    long_description=read('README.md'),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Customer Service',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.4',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
)
