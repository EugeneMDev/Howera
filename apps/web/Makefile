.PHONY: lint test test-unit golden-path check typecheck build

lint:
	npm run lint

test:
	npm run test

test-unit:
	npm run test:unit

golden-path:
	npm run test:golden-path

typecheck:
	npm run typecheck

build:
	npm run build

check: lint test typecheck build
