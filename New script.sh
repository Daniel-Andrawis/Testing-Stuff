#!/bin/bash
clear
echo "Import to Git From Notepad? Please enter Y or N"
read $CHOICE

if [ $CHOICE -eq "Y" ]
	then 
	echo "('-') Wroonnngg" 
	exit
else 
echo "\(^o^)/"
fi 

echo "Ok you got the first answer right. One more question? Do you live, laugh, love github? Answer by typing Y or N"
read $CHOICE2
if [ $CHOICE2 -eq "N" ]
	then 
	echo "('-') Wrong Choice"
	exit
else 
echo "You Passed Congrats"
fi 

echo "Get Scammed"
exit