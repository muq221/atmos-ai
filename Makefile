.PHONY: install pipeline train validate api test docker
install:   ; pip install -r requirements.txt
pipeline:  ; python -m atmos.pipeline.run
train:     ; python -m atmos.models.train
validate:  ; python scripts/validate_real_obs.py
api:       ; uvicorn atmos.api.app:app --reload
test:      ; pytest -q
docker:    ; docker compose up --build
