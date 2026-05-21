#!/bin/bash
# ============================================================
# build-opsync.sh — Automated OpSync Backend Build
# ============================================================
# Runs 5 Claude Code sessions sequentially (1-3) then in
# parallel (4-5) to build the complete Flask backend.
#
# Usage:
#   cd opsync-backend
#   chmod +x build-opsync.sh
#   ./build-opsync.sh
#
# Prerequisites:
#   - Claude Code CLI installed and authenticated
#   - Node.js / Python available in PATH
# ============================================================

set -e  # Exit on any error

echo "=========================================="
echo "  OpSync Backend — Automated Build"
echo "=========================================="
echo ""

# Ensure we're in the right directory
if [ ! -f "CLAUDE-00-MASTER.md" ]; then
    echo "ERROR: Run this script from the opsync-backend/ directory."
    echo "       Could not find CLAUDE-00-MASTER.md"
    exit 1
fi

# Set up CLAUDE.md as the master context
cp CLAUDE-00-MASTER.md CLAUDE.md
echo "[setup] CLAUDE.md set to master project context"
echo ""

# ──────────────────────────────────────────────
# SESSION 1: Project Setup & Environment
# ──────────────────────────────────────────────
echo "=========================================="
echo "  SESSION 1: Project Setup & Environment"
echo "=========================================="
claude -p "You are building the OpSync backend.

STEP 1: Read these files in order:
- CLAUDE-01-PROJECT-SETUP.md (your primary instructions)
- CLAUDE.md (master project context)
- HANDOFF.md (prior session state — may be empty)

STEP 2: Execute every step in CLAUDE-01-PROJECT-SETUP.md. Create all directories, files, and configurations exactly as specified.

STEP 3: Run the verification checklist at the end of the instruction file. Fix any issues.

STEP 4: Append your handoff section to HANDOFF.md using the template in that file. Include every file you created with full paths, any deviations, and verification results.

Do not skip the handoff step — the next session depends on it." \
  --allowedTools "Bash,Read,Write,Edit" --dangerously-skip-permissions

echo ""
echo "[session 1] COMPLETE"
echo ""

# ──────────────────────────────────────────────
# SESSION 2: Database Models
# ──────────────────────────────────────────────
echo "=========================================="
echo "  SESSION 2: Database Schema & Models"
echo "=========================================="
claude -p "You are building the OpSync backend. Session 1 (project setup) is complete.

STEP 1: Read these files in order:
- CLAUDE-02-DATABASE-MODELS.md (your primary instructions)
- CLAUDE.md (master project context)
- HANDOFF.md (Session 1's handoff — tells you exactly what files exist and their paths)

STEP 2: Trust HANDOFF.md for actual file paths and import patterns. If Session 1 deviated from the plan, use what it actually built.

STEP 3: Implement all 7 SQLAlchemy models exactly as specified in your instruction file.

STEP 4: Run every verification check. Fix any issues.

STEP 5: Append your handoff section to HANDOFF.md. Include exact table names, column names, relationship names, and verification output. Session 3 needs these details." \
  --allowedTools "Bash,Read,Write,Edit" --dangerously-skip-permissions

echo ""
echo "[session 2] COMPLETE"
echo ""

# ──────────────────────────────────────────────
# SESSION 3: API & Authentication
# ──────────────────────────────────────────────
echo "=========================================="
echo "  SESSION 3: REST API & Authentication"
echo "=========================================="
claude -p "You are building the OpSync backend. Sessions 1 (setup) and 2 (models) are complete.

STEP 1: Read these files in order:
- CLAUDE-03-API-AUTH.md (your primary instructions)
- CLAUDE.md (master project context)
- HANDOFF.md (Sessions 1 and 2 handoffs — tells you the actual model structure)

STEP 2: Before writing any code, verify the models work: run python -c 'from app.models import *; print(\"Models OK\")'

STEP 3: Use the actual model field names and to_dict() signatures from Session 2's handoff. If anything differs from your instruction file, trust the handoff.

STEP 4: Implement all API endpoints, JWT authentication, RBAC decorators, and service layer.

STEP 5: Write and run the pytest tests specified in verification.

STEP 6: Append your handoff to HANDOFF.md. Include all endpoints (method + path), JWT claims structure, and a working curl login example. Sessions 4 and 5 need the API surface." \
  --allowedTools "Bash,Read,Write,Edit" --dangerously-skip-permissions

echo ""
echo "[session 3] COMPLETE"
echo ""

# ──────────────────────────────────────────────
# SESSIONS 4 & 5: Seed Data + Algorithms (PARALLEL)
# ──────────────────────────────────────────────
echo "=========================================="
echo "  SESSIONS 4 & 5: Seed Data + Algorithms"
echo "  (running in parallel)"
echo "=========================================="

# Session 4: Seed Data (background)
claude -p "You are building the OpSync backend. Sessions 1-3 are complete.

STEP 1: Read these files in order:
- CLAUDE-04-SEED-DATA.md (your primary instructions)
- CLAUDE.md (master project context)
- HANDOFF.md (Sessions 1-3 handoffs — critical for knowing the actual model field names)

STEP 2: Before writing seed code, read the actual model files on disk to confirm field names:
  cat app/models/user.py
  cat app/models/restaurant.py
  cat app/models/shift.py
  cat app/models/operational_snapshot.py

STEP 3: Use the actual field names from the model files, not from your instruction file, if they differ.

STEP 4: Create the complete seed data script and Flask CLI command.

STEP 5: Run the seed script and verify all record counts.

STEP 6: Append your handoff to HANDOFF.md with record counts, test credentials, and the IDs of key records (active shifts, restaurant IDs)." \
  --allowedTools "Bash,Read,Write,Edit" --dangerously-skip-permissions &
PID_SEED=$!

# Session 5: Algorithms (background)
claude -p "You are building the OpSync backend. Sessions 1-3 are complete. Session 4 (seed data) may be running in parallel.

STEP 1: Read these files in order:
- CLAUDE-05-ALGORITHMS.md (your primary instructions)
- CLAUDE.md (master project context)
- HANDOFF.md (Sessions 1-3 handoffs — critical for model structure and API surface)

STEP 2: Read the actual model files to confirm field names:
  cat app/models/operational_snapshot.py
  cat app/models/recommendation.py
  cat app/models/alert.py

STEP 3: Check if seed data exists. If not, run: python -m app.seed.seed_data

STEP 4: Implement all three algorithm services (ForecastService, RecommendationEngine, AlertService) and the /api/dashboard/evaluate trigger endpoint.

STEP 5: Run verification — the algorithms should generate recommendations and alerts from the seeded data.

STEP 6: Append your handoff to HANDOFF.md." \
  --allowedTools "Bash,Read,Write,Edit" --dangerously-skip-permissions &
PID_ALGO=$!

# Wait for both parallel sessions
echo "  Waiting for Session 4 (seed data)  PID: $PID_SEED"
echo "  Waiting for Session 5 (algorithms) PID: $PID_ALGO"
wait $PID_SEED
echo "  [session 4] COMPLETE"
wait $PID_ALGO
echo "  [session 5] COMPLETE"

echo ""
echo "=========================================="
echo "  BUILD COMPLETE"
echo "=========================================="
echo ""
echo "  Next steps:"
echo "    1. Review HANDOFF.md for the full build log"
echo "    2. Run: python run.py"
echo "    3. Login: POST http://localhost:5000/api/auth/login"
echo "       email: manager@dallas.opsync.com"
echo "       password: manager123"
echo "    4. Dashboard: GET http://localhost:5000/api/dashboard/current"
echo ""
