PYTHON ?= python

.PHONY: test build lint run demo check clean publish-check release

test:
	$(PYTHON) -B scripts/dev.py test

build:
	$(PYTHON) -B scripts/dev.py release

lint:
	$(PYTHON) -B scripts/dev.py lint

run:
	$(PYTHON) -B scripts/dev.py run

demo:
	$(PYTHON) -B scripts/dev.py demo

check:
	$(PYTHON) -B scripts/dev.py check

clean:
	$(PYTHON) -B scripts/dev.py clean

publish-check:
	$(PYTHON) -B scripts/dev.py publish-check

release:
	$(PYTHON) -B scripts/dev.py release
