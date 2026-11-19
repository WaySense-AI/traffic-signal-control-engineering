.PHONY: all test examples

all:
	python3 run_all.py

test:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v

examples:
	PYTHONDONTWRITEBYTECODE=1 python3 run_all.py --examples-only
