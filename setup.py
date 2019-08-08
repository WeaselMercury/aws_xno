from os import path

from setuptools import setup

here = path.abspath(path.dirname(__file__))

setup(
    name='aws_xno',
    version='0.3.2',
    description='List EC2 resources on one account across regions and operations.',
    author='Xavier Nomicisio',
    classifiers=[
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    packages=['aws_xno'],
    install_requires=['boto3>=1.9.197', 'app_json_file_cache>=0.2.2'],
    entry_points={
        'console_scripts': [
            'aws_xno=aws_xno.__main__:main',
            'aws-xno=aws_xno.__main__:main',
        ],
    },
    package_data={'aws_xno':['aws_xno/*.json']},
)