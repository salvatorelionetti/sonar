install: /lib/systemd/system/sonar.service
	sudo apt-get install python-serial

/lib/systemd/system/sonar.service: sonar.service
	sudo cp sonar.service /lib/systemd/system
	# First time also start the service at startup
	sudo systemctl enable sonar.service

.PHONY: install
