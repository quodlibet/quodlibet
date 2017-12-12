#!/bin/bash

set -e

source env.sh

jhbuild build meta-bootstrap
jhbuild build quodlibet
