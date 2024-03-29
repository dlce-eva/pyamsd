from setuptools import setup, find_packages


setup(
    name='pyamsd',
    version='1.0.1.dev0',
    author='Hans-Jörg Bibiko',
    author_email='dlce.rdm@eva.mpg.de',
    description='Python library for AMSD data curation',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    keywords='',
    license='Apache 2.0',
    url='https://github.com/dlce-eva/pyamsd',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'amsd=pyamsd.__main__:main',
        ],
    },
    platforms='any',
    python_requires='>=3.6',
    install_requires=[
        'clldutils>=3.19.0',
        'cdstarcat>=1.4.0',
        'csvw>=3.1.3'
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-mock',
            'pytest-cov',
            'coverage>=5.5',
        ],
        'dev': ['flake8', 'twine'],
    },
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
)
