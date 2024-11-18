#!/bin/bash

#####
#
# start.sh - Start application
#
# Parameters:
#   None noted
#
# Copyright 2024 Broda Group Software Inc.
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.
#
# Created:  2024-07-22 by eric.broda@brodagroupsoftware.com
#####

# flask --app src.physrisk_api:create_app --debug run --host=0.0.0.0 --port=5000
# export PYTHONPATH=$(pwd)
# flask --app src.physrisk_api:create_app --debug run --host=0.0.0.0 --port=8081
python src/server.py