#!/usr/bin/env python

import os
from pkg_resources import parse_version
import shutil
import subprocess
import sys

import numpy as np

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext

if sys.version_info[0] < 3:
    import __builtin__ as builtins
else:
    import builtins
builtins.__LAP_SETUP__ = True

from distutils.command.clean import clean as Clean


class CleanCommand(Clean):
    description = "Remove build artifacts from the source tree"

    def run(self):
        Clean.run(self)
        if os.path.exists('build'):
            shutil.rmtree('build')
        # Remove c files if we are not within a sdist package
        cwd = os.path.abspath(os.path.dirname(__file__))
        remove_c_files = not os.path.exists(os.path.join(cwd, 'PKG-INFO'))
        if remove_c_files:
            if os.path.exists('lap/_lapjv.cpp'):
                os.unlink('lap/_lapjv.cpp')
        for dirpath, dirnames, filenames in os.walk('lap'):
            for filename in filenames:
                if any(filename.endswith(suffix) for suffix in
                       (".so", ".pyd", ".dll", ".pyc")):
                    os.unlink(os.path.join(dirpath, filename))
            for dirname in dirnames:
                if dirname == '__pycache__':
                    shutil.rmtree(os.path.join(dirpath, dirname))


def cythonize(cython_file, gen_file):
    try:
        from Cython.Compiler.Version import version as cython_version
        if parse_version(cython_version) < parse_version('0.21'):
            raise ImportError('Installed cython is too old (0.21 required), '
                              'please "pip install -U cython".')
    except ImportError:
        raise ImportError('Building lapjv requires cython, '
                          'please "pip install cython".')

    flags = ['--fast-fail']
    if gen_file.endswith('.cpp'):
        flags += ['--cplus']

    try:
        rc = subprocess.call(['cython'] + flags + ["-o", gen_file, cython_file])
        if rc != 0:
            raise Exception('Cythonizing %s failed' % cython_file)
    except OSError:
        rc = subprocess.call([sys.executable, '-c',
                              'import sys; from Cython.Compiler.Main import setuptools_main as main;'
                              ' sys.exit(main())'] + flags + ["-o", gen_file, cython_file])
        if rc != 0:
            raise Exception('Cythonizing %s failed' % cython_file)

def get_wrapper_pyx():
    return os.path.join('lap', '_lapjv.pyx')

def generate_cython():
    wrapper_pyx_file = get_wrapper_pyx()
    wrapper_c_file = os.path.splitext(wrapper_pyx_file)[0] + '.cpp'
    cythonize(wrapper_pyx_file, wrapper_c_file)

class BuildExt(build_ext):
    def run(self):
        generate_cython()
        super().run()


ext_modules = [
    Extension('lap._lapjv',
              sources=[
                  os.path.join('lap', '_lapjv.cpp'),
                  os.path.join('lap', 'lapjv.cpp'),
                  os.path.join('lap', 'lapmod.cpp')
              ],
              include_dirs=[np.get_include(), 'lap'])
]

def setup_package():
    metadata = dict(
        packages=['lap'],
        cmdclass={'build_ext': BuildExt, 'clean': CleanCommand},
        ext_modules=ext_modules,
    )

    if len(sys.argv) != 1 and not (
            len(sys.argv) >= 2 and ('--help' in sys.argv[1:] or
                                    sys.argv[1] in ('--help-commands',
                                                    'egg_info',
                                                    '--version',
                                                    'clean'))):
        print('Generating cython files')
        cwd = os.path.abspath(os.path.dirname(__file__))
        if not os.path.exists(os.path.join(cwd, 'PKG-INFO')):
            generate_cython()

    setup(**metadata)

if __name__ == "__main__":
    setup_package()
