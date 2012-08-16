#!/bin/bash

control_c() {
	echo ""
  	./calc.py results.txt
  	exit $?
}

trap control_c SIGINT

for i in `seq 100`;
do
	./webspd.py 2> /dev/null | tee -a results.txt
done
./calc.py results.txt
