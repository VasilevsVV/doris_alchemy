build:
	rm -rf ./dist
	python3 -m build

upload-test:
	python3 -m twine upload --repository testpypi dist/*

test-publish: build upload-test

upload:
	python3 -m twine upload --repository pypi dist/*

publish: build upload