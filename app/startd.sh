#!/bin/bash

#####
#
# startd.sh - Start application in docker
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

# NETWORK_NAME="localnet"
# docker network create $NETWORK_NAME

compose() {
  docker-compose -f $PROJECT_DIR/docker-compose.yml up
}

decompose() {
  docker-compose -f $PROJECT_DIR/docker-compose.yml down
}

compose;
decompose;