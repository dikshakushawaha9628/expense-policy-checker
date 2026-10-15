PY ?= python3
export PYTHONPATH := src

.PHONY: test demo edge clean data

test:           ## run the test-suite (stdlib unittest)
	$(PY) -m unittest discover -s tests -t . -v

demo:           ## full pipeline on the sample data
	$(PY) -m expense_checker run --as-of 2026-10-15

edge:           ## failure / edge-case demonstration
	$(PY) -m expense_checker edge-demo

data:           ## regenerate synthetic CSVs (seeded)
	$(PY) -m expense_checker generate --seed 42

clean:
	rm -rf output
