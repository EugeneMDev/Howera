.PHONY: lint test check

lint:
	python3 -m compileall app tests

test:
	HOWERA_CALLBACK_SECRET=$${HOWERA_CALLBACK_SECRET:-test-callback-secret} python3 -m unittest discover -s tests -p 'test_*.py' -v

check: lint test
