#!/bin/bash

set -e

cd quodlibet
MSYSTEM= python3 -R -bb setup.py test
