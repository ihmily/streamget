from setuptools import find_packages, setup

with open('README.md', encoding='utf-8') as f:
    readme = f.read()

setup(
    name='streamget',
    version='4.0.6',
    author='Hmily',
    description='A Multi-Platform Live Stream Parser Library.',
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/ihmily/streamget',
    project_urls={
        "Documentation": "https://streamget.readthedocs.io",
        "Source": "https://github.com/ihmily/streamget"
    },
    include_package_data=True,
    package_data={
        'streamget': ['js/*.js'],
    },
    packages=find_packages(),
    install_requires=[
        'requests>=2.31.0',
        'loguru>=0.7.3',
        'pycryptodome>=3.20.0',
        'distro>=1.9.0',
        'tqdm>=4.67.1',
        'httpx[http2]>=0.28.1',
        'PyExecJS>=1.5.1',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
    entry_points={
        'console_scripts': [
            'streamget=streamget.cli:main'
        ]
    }
)
