from setuptools import setup, find_packages

setup(
    name="prometheus-dirsize-exporter",
    version="1.0",
    packages=find_packages(),
    license="3-BSD",
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
