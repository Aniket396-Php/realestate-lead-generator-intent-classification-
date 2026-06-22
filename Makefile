# ─────────────────────────────────────────────────────────
#  Property Brix AI Chatbot
#  Usage: make <target>
# ─────────────────────────────────────────────────────────

PYTHON  = backend/venv/Scripts/python
PIP     = backend/venv/Scripts/pip

# ── Setup ─────────────────────────────────────────────────
venv:
	python -m venv backend/venv
	@echo "Virtual environment created."

install: venv
	$(PIP) install -r backend/requirements.txt
	@echo "Dependencies installed."

# ── Start chatbot backend (port 8001) ─────────────────────
start:
	cd backend && ../backend/venv/Scripts/python -m uvicorn app.main:app --reload --port 8001

# ── Maintenance ───────────────────────────────────────────
clean:
	Remove-Item -Recurse -Force backend/app/__pycache__ -ErrorAction SilentlyContinue
	@echo "Cache cleaned."

.PHONY: venv install start clean
