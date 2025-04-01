#!/bin/bash

pip install --upgrade pip setuptools wheel twine build

rm -rf build/ dist/ *.egg-info/

python -m build

twine check dist/*

echo "Build completed. To upload to PyPI, run: twine upload dist/*"
