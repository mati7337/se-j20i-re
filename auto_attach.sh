while [ 1 ]
do
	port_status="$(usbip port | wc -l)"

	if [ "$port_status" = "2" ]
	then
		echo "Trying to attach"
		usbip attach -r 127.0.0.1 -b 1-1
	else
		echo "Already attached"
	fi

	sleep 0.5
done
