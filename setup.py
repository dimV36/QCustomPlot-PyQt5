#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import platform
import subprocess

import sipconfig

from distutils.core import DistutilsError
from distutils.sysconfig import customize_compiler
from os.path import join, exists, abspath, dirname

from setuptools import setup, Extension

from sipdistutils import build_ext

from PyQt5.QtCore import PYQT_CONFIGURATION
from PyQt5.QtCore import QLibraryInfo


WINDOWS_HOST = (platform.system() == 'Windows')
LINUX_HOST = (platform.system() == 'Linux')

# This is with Unix pathsep even on windows
QT_BINARIES = QLibraryInfo.location(QLibraryInfo.BinariesPath)
if WINDOWS_HOST:
    # Default to MSVC nmake
    DEFAULT_MAKE = 'jom.exe'
    DEFAULT_QMAKE = "{}/{}".format(QT_BINARIES, "qmake.exe")
else:
    DEFAULT_MAKE = 'make'
    DEFAULT_QMAKE = "{}/{}".format(QT_BINARIES, "qmake")
DEFAULT_QT_INCLUDE = QLibraryInfo.location(QLibraryInfo.HeadersPath)
ROOT = abspath(dirname(__file__))
BUILD_STATIC_DIR = join(ROOT, 'lib-static')


class MyBuilderExt(build_ext):
    user_options = build_ext.user_options[:]
    user_options += [
        ('qmake=', None, 'Path to qmake'),
        ('qt-include-dir=', None, 'Path to Qt headers'),
        ('qt-library-dir=', None, 'Path to Qt library dir (used at link time)'),
        ('make=', None, 'Path to make')
    ]

    def initialize_options(self):
        build_ext.initialize_options(self)
        self.qmake = None
        self.qt_include_dir = None
        self.qt_library_dir = None
        self.make = None
        self.static_lib = None
        pyqt_sip_config = PYQT_CONFIGURATION['sip_flags']
        if self.sip_opts is None:
            self.sip_opts = pyqt_sip_config
        else:
            self.sip_opts += pyqt_sip_config

    def finalize_options(self):
        build_ext.finalize_options(self)
        if self.qmake is None:
            print('Setting qmake to \'%s\'' % DEFAULT_QMAKE)
            self.qmake = DEFAULT_QMAKE
        if self.make is None:
            print('Setting make to \'%s\'' % DEFAULT_MAKE)
            self.make = DEFAULT_MAKE
        if self.qt_include_dir is None:
            pipe = subprocess.Popen([self.qmake, "-query", "QT_INSTALL_HEADERS"], stdout=subprocess.PIPE)
            (stdout, stderr) = pipe.communicate()
            self.qt_include_dir = str(stdout.strip(), 'utf8')
            print('Setting Qt include dir to \'%s\'' % self.qt_include_dir)

        if self.qt_library_dir is None:
            pipe = subprocess.Popen([self.qmake, "-query", "QT_INSTALL_LIBS"], stdout=subprocess.PIPE)
            (stdout, stderr) = pipe.communicate()
            self.qt_library_dir = str(stdout.strip(), 'utf8')
            print('Setting Qt library dir to \'%s\'' % self.qt_library_dir)

        if not exists(self.qmake):
            raise DistutilsError('Could not determine valid qmake at %s' % self.qmake)

    def __build_qcustomplot_library(self):
        if WINDOWS_HOST:
            qcustomplot_static = join(self.build_temp, 'release', 'qcustomplot.lib')
        else:
            qcustomplot_static = join(self.build_temp, 'libqcustomplot.a')
        if exists(qcustomplot_static):
            return

        os.makedirs(self.build_temp, exist_ok=True)
        os.chdir(self.build_temp)
        print('Make static qcustomplot library...')
        self.spawn([self.qmake, join(ROOT, 'QCustomPlot/src/qcp-staticlib.pro')])
        self.spawn([self.make])
        os.chdir(ROOT)
        self.static_lib = qcustomplot_static
        # Possibly it's hack
        qcustomplot_ext = self.extensions[0]
        qcustomplot_ext.extra_objects = [qcustomplot_static]

    def build_extensions(self):
        customize_compiler(self.compiler)
        try:
            self.compiler.compiler_so.remove('-Wstrict-prototypes')
        except (AttributeError, ValueError):
            pass
        self.__build_qcustomplot_library()
        # Possibly it's hack
        qcustomplot_ext = self.extensions[0]
        qcustomplot_ext.include_dirs += [
            join(self.qt_include_dir, subdir)
            for subdir in ['.', 'QtCore', 'QtGui', 'QtWidgets', 'QtPrintSupport']
        ]
        qcustomplot_ext.library_dirs += [
            self.build_temp,
            self.qt_library_dir
        ]

        qcustomplot_ext.libraries = [
            'Qt5Core',
            'Qt5Gui',
            'Qt5Widgets',
            'Qt5PrintSupport',
            'qcustomplot'
        ]

        if WINDOWS_HOST:
            qcustomplot_ext.library_dirs.append(join(self.build_temp, 'release'))
            qcustomplot_ext.libraries.append('Opengl32')

        build_ext.build_extensions(self)

    def _sip_sipfiles_dir(self):
        cfg = sipconfig.Configuration()
        return join(cfg.default_sip_dir, 'PyQt5')

setup(
    name='QCustomPlot',
    version='2.0.0',
    description='QCustomPlot is a PyQt5 widget for plotting and data visualization',
    author='Dmitry Voronin, Giuseppe Corbelli',
    author_email='carriingfate92@yandex.ru',
    url='https://github.com/dimv36/QCustomPlot-PyQt5',
    platforms=['Linux'],
    license='MIT',
    ext_modules=[
        Extension(
            'QCustomPlot',
            ['all.sip'],
            include_dirs=['.']
        ),
    ],
    requires=[
        'sipconfig',
        'PyQt5'
    ],
    cmdclass={'build_ext': MyBuilderExt}
)
