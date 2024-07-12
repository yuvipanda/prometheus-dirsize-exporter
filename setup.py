from setuptools import setup, find_packages

with open("README.md") as f:
    long_description = f.read()

setup(
    name="prometheus-dirsize-exporter",
    version="3.2",
    packages=find_packages(),
    license="3-BSD",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="yuvipanda",
    author_email="yuvipanda@gmail.com",
    install_requires=[
        "prometheus-client",
    ],
    entry_points={
        'console_scripts': [
            'dirsize-exporter = prometheus_dirsize_exporter.exporter:main',
        ]
    }
)
