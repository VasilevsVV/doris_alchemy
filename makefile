build:
	rm -rf ./dist
	python -m build

upload-test:
	python -m twine upload --repository testpypi dist/*

test-publish: build upload-test

upload:
	python -m twine upload --repository pypi dist/*

publish: build upload