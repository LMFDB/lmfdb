# LMFDB Development Environment Instructions

The L-functions and Modular Forms Database (LMFDB) is a large Flask-based mathematical web application built on SageMath that provides access to mathematical objects including elliptic curves, number fields, modular forms, and L-functions.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Essential Setup & Build Commands

**Environment Setup (NEVER CANCEL - takes 20+ minutes):**
```bash
# Create conda environment with Sage 10.4
conda env create -f .environment.yml  # Takes 20+ minutes, set timeout to 60+ minutes

# Activate environment (required for all commands)
source /usr/share/miniconda/etc/profile.d/conda.sh
conda activate lmfdb

# Install Python dependencies (NEVER CANCEL - takes 2-3 minutes)
sage -pip install -r requirements.txt  # Set timeout to 10+ minutes
```

**Linting & Code Quality (NEVER CANCEL - takes 45+ seconds):**
```bash
# Run full linting suite - ALWAYS run before committing
tox -e lint  # Takes 45 seconds, set timeout to 5+ minutes

# Alternative linting commands
./codestyle.sh  # Runs pycodestyle checks
pyflakes start-lmfdb.py user-manager.py lmfdb/
```

**Testing (Database required - see limitations below):**
```bash
# Full test suite (requires database connection)
./test.sh  # Takes 10+ minutes when working, set timeout to 30+ minutes

# Run specific test modules
sage -python -m pytest lmfdb/hypergm/test_hgm.py -v
```

## Database and Runtime Configuration

**Database Connection:**
- Default configuration uses read-only database at `devmirror.lmfdb.xyz`
- Local database setup requires PostgreSQL and is complex
- Application creates `config.ini` automatically on first run
- Tests and runtime require network access to database

**Server Startup (requires database):**
```bash
# Start development server with debug mode
sage -python start-lmfdb.py --debug  # Runs on http://localhost:37777

# Server options
sage -python start-lmfdb.py --help  # Show all options
sage -python start-lmfdb.py --port 37778 --debug  # Custom port
```

**LIMITATION:** The application cannot run locally without database access. Tests and server startup will fail with `psycopg2.OperationalError` if `devmirror.lmfdb.xyz` is unreachable.

## Project Structure & Navigation

**Main Application Code:**
- `lmfdb/` - Main application directory with mathematical modules
  - `elliptic_curves/` - Elliptic curves over Q and number fields
  - `number_fields/` - Global number fields
  - `modular_forms/` - Classical and Hilbert modular forms  
  - `lfunctions/` - L-functions (~2090 lines in main.py)
  - `characters/` - Dirichlet and Hecke characters
  - `galois_groups/` - Galois groups
  - `genus2_curves/` - Genus 2 curves
  - `local_fields/` - Local fields (~1883 lines in main.py)

**Key Files:**
- `start-lmfdb.py` - Application entry point
- `lmfdb/website.py` - Main Flask application setup
- `lmfdb/app.py` - Flask app configuration (25K+ lines)
- `lmfdb/lmfdb_database.py` - Database interface layer
- `requirements.txt` - Python dependencies
- `.environment.yml` - Conda environment specification

**Configuration:**
- `config.ini` - Auto-generated database and Flask configuration
- `tox.ini` - Test runner configuration
- `test.sh` - Main test script
- `codestyle.sh` - Code style checking

## Validation & CI Requirements

**Before Committing (CRITICAL):**
```bash
# ALWAYS run linting - CI will fail without this
tox -e lint  # Must pass before committing

# Code style validation
./codestyle.sh

# Check pyflakes errors
pyflakes start-lmfdb.py user-manager.py lmfdb/
```

**GitHub Actions CI:**
- Uses matrix testing across different database configurations
- Requires conda environment setup (~20 minutes)
- Runs pytest with parallel execution using tox
- Linting must pass (pyflakes, pylint, ruff)
- Tests require database access (not available in local development)

## Common Development Tasks

**Adding New Mathematical Objects:**
1. Create new module in `lmfdb/` following existing patterns
2. Follow URL conventions in Development.md (e.g., `/ModularForm/GL2/Q/holomorphic/`)
3. Create database tables using `db.create_table()` (see Postgres_FAQ.md)
4. Add Flask blueprint registration in `lmfdb/website.py`
5. Create templates in module's `templates/` directory
6. Add tests in module's `test_*.py` files

**Key Development Files to Check:**
- `lmfdb/utils/search_parsing.py` - Search functionality (~1892 lines)
- `lmfdb/classical_modular_forms/main.py` - Example complex module (~1780 lines)
- `Development.md` - Detailed development guidelines
- `StyleGuide.md` - HTML/CSS styling conventions
- `Postgres_FAQ.md` - Database interaction documentation

**Template System:**
- Uses Flask + Jinja2 templates
- Base template: `lmfdb/templates/homepage.html`
- Common template variables: `title`, `properties`, `bread`, `sidebar`
- CSS in `lmfdb/templates/style.css`

## Technology Stack

**Core Technologies:**
- **SageMath 10.4** - Mathematical computation system
- **Flask 3.1.1** - Web framework
- **PostgreSQL** - Database (via psycodict abstraction)
- **Jinja2** - Template engine
- **pytest** - Testing framework

**Key Dependencies:**
- `psycodict` - Database abstraction layer
- `psycopg2-binary` - PostgreSQL adapter
- `flask-login` - User authentication
- `bcrypt` - Password hashing
- `pyyaml` - YAML processing

**Build Tools:**
- `conda` - Environment management
- `tox` - Test runner and automation
- `pyflakes`, `pylint`, `ruff` - Code quality tools

## Timing Expectations & Timeouts

**NEVER CANCEL these operations:**
- `conda env create -f .environment.yml` - 20+ minutes (set timeout: 60+ minutes)
- `sage -pip install -r requirements.txt` - 2-3 minutes (set timeout: 10+ minutes)
- `tox -e lint` - 45 seconds (set timeout: 5+ minutes)
- `./test.sh` - 10+ minutes when working (set timeout: 30+ minutes)

**Quick Operations:**
- Environment activation: 1-2 seconds
- `./codestyle.sh`: <5 seconds
- `sage --version`: <2 seconds

## Repository Statistics

- **51 main modules** in lmfdb/ directory
- **40+ test files** across the codebase
- **71,000+ lines** of Python code
- **Complex mathematical application** with deep domain expertise required
- **Large contributor base** (see CONTRIBUTORS.yaml)

## Working Effectively

**Daily Development Workflow:**
1. Always activate conda environment first
2. Run `tox -e lint` before making changes to ensure clean baseline
3. Make minimal, surgical code changes
4. Test changes locally (limited without database access)
5. Run `tox -e lint` before committing
6. Check that pyflakes shows no new errors

**Code Style:**
- Follow existing patterns in similar modules
- Use mathematical URL conventions from Development.md
- Create knowls for mathematical terminology
- Include proper credits and documentation
- Update related templates and tests

This codebase requires significant mathematical domain knowledge and familiarity with web development patterns. Always consult the existing documentation and similar modules when making changes.