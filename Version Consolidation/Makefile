# Paths (edit if you like)
IN_DIR := ./_incoming_all_iterations
OUT_DIR := ./rulesets

.PHONY: consolidate clean

consolidate:
	python3 consolidate_rulesets.py --in $(IN_DIR) --out $(OUT_DIR) --single

clean:
	rm -rf $(OUT_DIR)/_reports $(OUT_DIR)/overrides $(OUT_DIR)/ruleset.main.yaml || true
