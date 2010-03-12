#!/usr/bin/python

from distutils.core import setup, Extension
import sys

setup(name='python-nagdata',
    version='0.1',
    description='Python interface to Nagios object and status files',
    license='LGPL3',
    author='Alexander Duryagin',
    author_email='daa@vologda.ru',
    url='http://github.com/daa/nagdata',
    packages=['nagdata'],
    ext_modules= [
        Extension('nagdata/cparser_fmt', ['nagdata/cparser.c'],
            define_macros=[
                ('WITH_FORMAT', None),
                ('initfunc_name', 'initcparser_fmt'),
                ('cparser_name', '"cparser_fmt"')]),
        Extension('nagdata/cparser_fast', ['nagdata/cparser2.c'],
            define_macros=[
                ('initfunc_name', 'initcparser_fast'),
                ('cparser_name', '"cparser_fast"')]) ])

