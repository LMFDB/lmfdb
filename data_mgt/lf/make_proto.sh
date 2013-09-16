#!/usr/bin/env bash
cd `dirname "$0"`
protoc -I. --python_out=. lf.proto

