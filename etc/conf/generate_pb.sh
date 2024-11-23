#!/bin/bash
set -e 

cd ../

echo "|>>| Generating options protobuf..."
docker run --rm -v $(pwd):$(pwd) -w $(pwd) luizcarloscf/docker-protobuf:master \
                                                        --python_out=.\
                                                        -I./conf/ options.proto
echo "|>>| Done!"

echo "|>>| Generating msgs protobuf..."
docker run --rm -v $(pwd):$(pwd) -w $(pwd) luizcarloscf/docker-protobuf:master \
                                                        --python_out=.\
                                                        -I./conf/ msgs.proto
echo "|>>| Done!"