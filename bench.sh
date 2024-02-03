#!/bin/bash
java -jar target/date-time-wars.jar ".*\.parse" -bm avgt -w 6 -wi 5 -r 6 -i 5 -f 1 -prof async:libPath=/home/morten/Downloads/async-profiler-3.0-linux-x64/lib/libasyncProfiler.so -v EXTRA -rf json

