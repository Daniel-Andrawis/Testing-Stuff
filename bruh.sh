#!/bin/bash 
echo "Please Enter Password"
read password 
if [ "$password" == "123" ]
then 
	echo "Confirmed"
else 
	echo "Not Allowed"
exit 
fi
echo  "Please enter your name:"
read name 
if [ "$name" == "liam" ]
then 
	echo "No Bitches?"
elif  [ "$name" == "neel" ]
then 
	echo "No Bitches?"
else 
	echo "You seem cool"
fi

