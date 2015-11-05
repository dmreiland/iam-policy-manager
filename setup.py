from setuptools import setup

setup(
    name='aws',
    version='1.0.1',
    packages=['csmutils','awsutils','utils'],
    include_package_data=True,
    install_requires=[
        'boto3',
        'click',
        'colorama',
        'jinja2'
    ],
    entry_points='''
        [console_scripts]
        policies=csmutils.policies:main
        manage=cli:cli
    ''',
)
