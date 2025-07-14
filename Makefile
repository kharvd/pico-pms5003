shell:
	minicom -o -D /dev/tty.usbmodem2101

cat:
	rshell -p /dev/tty.usbmodem2101 --buffer-size 512 cat /pyboard/main.py

sync:
	rshell -p /dev/tty.usbmodem2101 --buffer-size 512 cp main.py /pyboard/main.py

