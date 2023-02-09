#!/bin/bash 

echo "Started"
if [ $# -eq 1 ]; then    
  N=$1
  echo "Working on it"

  var1=0
  var2=1

  echo $var1

  if [ $N -eq  1 ]; then
    exit 0
  fi 

  echo $var2

  if [ $N -eq 2 ]; then 
    exit 0
  fi

  for  (( i=2; i<=N; i++ )); do 
    sum=$(($var1 + $var2))    
    echo $sum
    var1=$var2
    var2=$sum
  done
else
  echo "Please provide a number as the only argument."
fi
