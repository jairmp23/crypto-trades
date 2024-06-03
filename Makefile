VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

.PHONY: install
install: requirements.txt
	@python3 -m venv $(VENV) 
	@$(PIP) install -r requirements.txt

.PHONY: test
test:
	@$(VENV)/bin/coverage run -m pytest
	@$(VENV)/bin/coverage report

.PHONY: clean
clean:
	@rm -rf $(VENV)
	@rm -rf .pytest_cache
	@rm -f .coverage
