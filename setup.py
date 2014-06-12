from setuptools import setup, find_packages

setup(
    name='PyEngineIO',
    version='1.2.1-beta',
    url='http://github.com/fuzeman/PyEngineIO/',

    author='Dean Gardiner',
    author_email='me@dgardiner.net',

    description='Python implementation of engine.io',
    packages=find_packages(),
    platforms='any',

    install_requires=[
        'PyEmitter',
        'PyEngineIO-Parser',

        'gevent',
        'gevent-websocket'
    ],

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python'
    ],
)
