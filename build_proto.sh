#!/bin/bash

# Generate Python files from proto files
mkdir -p src/proto
touch src/proto/.gitignore && echo "*" > src/proto/.gitignore
protoc --proto_path=proto --python_out=src/proto --mypy_out=src/proto proto/*.proto

# Adjust imports in generated Python files to use relative imports
find src/proto -name "*.py" -exec sed -i 's/^import \([^ ]*\)_pb2 as \([^ ]*\)$/from . import \1_pb2 as \2/' {} \;
