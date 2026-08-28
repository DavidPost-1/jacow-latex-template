.PHONY: all clean

PROJECT  := main
SRC_DIR  := src
TEMP_DIR := .temp

all:
	@mkdir -p $(SRC_DIR)/$(TEMP_DIR)
	latexmk -pdf -cd \
		-pdflatex="pdflatex -synctex=1 -interaction=nonstopmode -halt-on-error" \
		-outdir=$(TEMP_DIR) -auxdir=$(TEMP_DIR) \
		$(SRC_DIR)/$(PROJECT).tex
	cp $(SRC_DIR)/$(TEMP_DIR)/$(PROJECT).pdf $(SRC_DIR)/$(PROJECT).pdf
	cp $(SRC_DIR)/$(TEMP_DIR)/$(PROJECT).synctex.gz $(SRC_DIR)/$(PROJECT).synctex.gz

clean:
	latexmk -C -cd -outdir=$(TEMP_DIR) $(SRC_DIR)/$(PROJECT).tex
	rm -rf $(SRC_DIR)/$(TEMP_DIR)

submission:
	uv run build_submission.py $(SRC_DIR)/$(PROJECT).tex