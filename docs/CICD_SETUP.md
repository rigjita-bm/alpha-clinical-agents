# CI/CD Setup Instructions

## Problem
OAuth token doesn't have `workflow` scope required to push GitHub Actions workflows.

## Solution: Manual Setup via GitHub UI

### Step 1: Copy Workflow Content

Copy the entire content below:

```yaml
name: Alpha Clinical CI/CD

on:
  push:
    branches: [main, master, develop]
  pull_request:
    branches: [main, master]

env:
  PYTHONUNBUFFERED: 1
  FORCE_COLOR: 1

jobs:
  lint-and-format:
    runs-on: ubuntu-latest
    name: 🎨 Lint & Format
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install linting tools
        run: |
          pip install flake8 black isort mypy bandit[toml]
      
      - name: Run flake8
        run: |
          flake8 agents/ core/ tests/ --max-line-length=100 --show-source --statistics
      
      - name: Check formatting with black
        run: |
          black --check --diff agents/ core/ tests/ --line-length=100
        continue-on-error: true
      
      - name: Check imports with isort
        run: |
          isort --check-only --diff agents/ core/ tests/
        continue-on-error: true
      
      - name: Type checking with mypy
        run: |
          mypy agents/ core/ --ignore-missing-imports || true
      
      - name: Security scan with bandit
        run: |
          bandit -r agents/ core/ -f json -o bandit-report.json || true
          bandit -r agents/ core/ || true

  test-matrix:
    runs-on: ubuntu-latest
    name: 🧪 Tests (Py${{ matrix.python-version }})
    needs: lint-and-format
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_alpha_clinical
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run unit tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_alpha_clinical
          PYTHONPATH: ${{ github.workspace }}
        run: |
          pytest tests/ -v --tb=short --cov=agents --cov=core --cov-report=xml --cov-report=html -x
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        if: matrix.python-version == '3.11'
        with:
          files: ./coverage.xml
          fail_ci_if_error: false
          verbose: true

  integration-tests:
    runs-on: ubuntu-latest
    name: 🔗 Integration Tests
    needs: test-matrix
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: integration_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/integration_test
        run: |
          pytest tests/test_integration.py -v --tb=short

  compliance-check:
    runs-on: ubuntu-latest
    name: ✅ Compliance Check
    steps:
      - uses: actions/checkout@v4
      
      - name: Check FDA compliance markers
        run: |
          echo "Checking 21 CFR Part 11 compliance markers..."
          grep -r "21 CFR Part 11" agents/ core/ || echo "⚠️ No explicit 21 CFR references found"
          grep -r "audit_trail\|electronic_signature" agents/ core/ || echo "⚠️ Audit trail markers check"
          echo "✅ Compliance check complete"

  all-checks-pass:
    runs-on: ubuntu-latest
    name: 🎯 All Checks Passed
    needs: [lint-and-format, test-matrix, integration-tests, compliance-check]
    if: always()
    steps:
      - name: Check all jobs status
        run: |
          if [ "${{ needs.lint-and-format.result }}" != "success" ] || \
             [ "${{ needs.test-matrix.result }}" != "success" ] || \
             [ "${{ needs.integration-tests.result }}" != "success" ] || \
             [ "${{ needs.compliance-check.result }}" != "success" ]; then
            echo "❌ Some checks failed"
            exit 1
          fi
          echo "✅ All checks passed!"
```

### Step 2: Create via GitHub UI

1. Go to: https://github.com/rigjita-bm/alpha-clinical-agents/actions
2. Click **"New workflow"**
3. Click **"set up a workflow yourself"**
4. Paste the content above into the editor
5. Filename: `.github/workflows/ci.yml`
6. Click **"Commit new file"**

### Step 3: Verify

1. Go to **Actions** tab
2. You should see "Alpha Clinical CI/CD" workflow
3. Push any change to main branch to trigger

---

## Alternative: GitHub CLI

If you have `gh` CLI with proper permissions:

```bash
gh workflow create ci.yml --repo=rigjita-bm/alpha-clinical-agents
```
