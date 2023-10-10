from setuptools import find_packages, setup

setup(
   name='foo',
   version='1.0',
   description='A useful module',
   license='GPLv3',
   packages=find_packages(),
   setup_requires=['libsass >= 0.6.0'],
   sass_manifests={
      '.': {
        'sass_path': 'static/sass',
        'css_path': 'static/css',
        'strip_extension': True,
    	},
   }
)
