.PHONY: all data pipeline screenshots deliverables dashboard-screenshots test clean

all: data pipeline

data:
	python data/generate_data.py

pipeline:
	python -m close_pack

screenshots:
	python docs/generate_screenshots.py

deliverables: pipeline
	mkdir -p deliverables
	cp output/kpi_dashboard.xlsx output/variance_analysis.xlsx output/close_checklist.xlsx deliverables/

dashboard-screenshots: deliverables
	python docs/generate_dashboard_screenshots.py

test:
	python -m unittest discover -s tests -v

clean:
	rm -f data/close_pack.db
	rm -rf output/*.xlsx
