


.PHONY: clear
clear:
	find . -name "*:Zone.Identifier" -type f -delete
	find . -name "*.aux" -type f -delete
	find . -name "*.gz" -type f -delete
	find . -name "*.out" -type f -delete
	find . -name "*.txss2" -type f -delete
	find . -name "*.log" -type f -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	
.PHONY: uipy
uipy:
	pyuic5 ./mod7_5/ui/mainWindow.ui -o ui.py

