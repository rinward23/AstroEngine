MAMBA ?= micromamba
ENV_NAME ?= astroengine

.PHONY: env
env:
	$(MAMBA) env create -f environment.yml -n $(ENV_NAME) || \
	$(MAMBA) env update -f environment.yml -n $(ENV_NAME)

.PHONY: test
test:
	pytest -q
