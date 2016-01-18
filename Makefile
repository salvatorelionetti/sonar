install: /lib/systemd/system/sonar.service

/lib/systemd/system/sonar.service: sonar.service
	sudo cp sonar.service /lib/systemd/system
	# First time also start the service at startup
	sudo systemctl enable sonar.service

.PHONY: install
