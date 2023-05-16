#!/bin/bash

git clone https://github.com/wesolowskip/mgr-parser.git -b rmm meta-json-parser

cd meta-json-parser
git clone https://github.com/CLIUtils/CLI11.git -b v2.0.0 third_parties/CLI11
git clone https://github.com/boostorg/mp11.git -b boost-1.82.0 third_parties/mp11
git submodule update --init --recursive # git clone nie dzialalo (prawdopodbnie zla wersja)
