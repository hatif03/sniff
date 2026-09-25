# Sherlock Deployment Guide

This guide covers all methods to deploy and distribute Sherlock as a Python package.

## Prerequisites

1. **Python 3.11+** installed
2. **Build tools** installed:
   ```bash
   pip install build twine
   ```

3. **Git repository** (for version control and GitHub distribution)

---

## 🔒 Security: NEVER Include Credentials in Package

**CRITICAL: AWS credentials must NEVER be included in the package build.**

### What Gets Excluded from the Build

The following files are excluded via `.gitignore` and should NEVER be in the package:
- `.env` files (contains AWS credentials)
- `data/` directory (contains run history database)
- `artifacts/` directory (contains test run evidence)
- Any files with AWS keys, tokens, or secrets

### What IS Included in the Build

Only these files are packaged:
- Source code (`src/` directory)
- Persona templates (`src/personas/*.json`)
- Package metadata (`pyproject.toml`)
- Documentation (`README.md`)
- `.env.example` (template only, no actual credentials)

### How Users Configure Credentials

After installation, users configure their own credentials using one of these methods:

1. **AWS Profile** (Recommended):
   ```bash
   aws configure --profile sherlock
   ```

2. **Environment Variables**:
   ```bash
   export AWS_ACCESS_KEY_ID=...
   export AWS_SECRET_ACCESS_KEY=...
   ```

3. **Local .env File**:
   Users create their own `.env` from `.env.example`

### Pre-Build Security Checklist

Before building, ensure:
- [ ] `.env` is in `.gitignore`
- [ ] No AWS credentials in code or config files
- [ ] `.env.example` has placeholder values only
- [ ] `artifacts/` and `data/` are excluded
- [ ] No API keys, tokens, or secrets in any committed files

---

## Method 1: Build Distributable Package Files

This creates `.whl` and `.tar.gz` files you can share directly.

### Step 1: Clean Previous Builds

```bash
rm -rf dist/ build/ *.egg-info
```

### Step 2: Build the Package

```bash
python -m build
```

This creates:
- `dist/sherlock-0.1.0-py3-none-any.whl` (wheel file)
- `dist/sherlock-0.1.0.tar.gz` (source distribution)

### Step 3: Test Installation Locally

```bash
# Create a test virtual environment
python -m venv test-env
source test-env/bin/activate  # On Windows: test-env\Scripts\activate

# Install from wheel
pip install dist/sherlock-0.1.0-py3-none-any.whl

# Install Playwright browsers
playwright install

# Test the installation
sherlock --help

# Deactivate when done
deactivate
```

### Step 4: Distribute

Share the `.whl` file with users. They can install it with:
```bash
pip install sherlock-0.1.0-py3-none-any.whl
playwright install
```

---

## Method 2: Publish to PyPI

This allows users to install with `pip install sherlock`.

### Step 1: Create PyPI Accounts

1. **Production PyPI**: https://pypi.org/account/register/
2. **Test PyPI** (recommended for testing): https://test.pypi.org/account/register/

### Step 2: Create API Tokens

**For Test PyPI:**
1. Go to https://test.pypi.org/manage/account/token/
2. Click "Add API token"
3. Name: `sherlock-test`
4. Scope: "Entire account" or specific project
5. Copy the token (starts with `pypi-`)

**For Production PyPI:**
1. Go to https://pypi.org/manage/account/token/
2. Follow same steps as above
3. Name: `sherlock-production`

### Step 3: Configure Credentials

Create `~/.pypirc`:

```bash
cat > ~/.pypirc << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_PRODUCTION_TOKEN_HERE

[testpypi]
username = __token__
password = pypi-YOUR_TEST_TOKEN_HERE
EOF

# Secure the file
chmod 600 ~/.pypirc
```

### Step 4: Build Package

```bash
rm -rf dist/ build/ *.egg-info
python -m build
```

### Step 5: Upload to Test PyPI (Recommended First)

```bash
twine upload --repository testpypi dist/*
```

### Step 6: Test Installation from Test PyPI

```bash
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            sherlock

playwright install
sherlock --help
```

### Step 7: Upload to Production PyPI

Once testing is successful:

```bash
twine upload dist/*
```

Now anyone can install with:
```bash
pip install sherlock
playwright install
```

### Step 8: Verify on PyPI

Check your package page:
- Production: https://pypi.org/project/sherlock/
- Test: https://test.pypi.org/project/sherlock/

---

## Method 3: Install from GitHub

Users can install directly from your GitHub repository.

### Prerequisites

1. Push code to GitHub:
   ```bash
   git add .
   git commit -m "Release v0.1.0"
   git push origin main
   ```

2. Create a release tag:
   ```bash
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin v0.1.0
   ```

### Installation Methods

**From main branch:**
```bash
pip install git+https://github.com/abbasalisariya/sherlock.git
```

**From specific tag:**
```bash
pip install git+https://github.com/abbasalisariya/sherlock.git@v0.1.0
```

**From specific branch:**
```bash
pip install git+https://github.com/abbasalisariya/sherlock.git@develop
```

**Editable install for development:**
```bash
git clone https://github.com/abbasalisariya/sherlock.git
cd sherlock
pip install -e .
```

---

## Method 4: GitHub Releases

Create a formal GitHub release with downloadable assets.

### Step 1: Build Package

```bash
python -m build
```

### Step 2: Create GitHub Release

1. Go to your repository on GitHub
2. Click "Releases" → "Create a new release"
3. Tag version: `v0.1.0`
4. Release title: `Sherlock v0.1.0 - Initial Release`
5. Description: Copy relevant sections from CHANGELOG
6. Attach files:
   - `dist/sherlock-0.1.0-py3-none-any.whl`
   - `dist/sherlock-0.1.0.tar.gz`
7. Publish release

### Step 3: Users Download and Install

Users can download the wheel from the release page and install:
```bash
pip install sherlock-0.1.0-py3-none-any.whl
```

---

## Method 5: Docker Container (Optional)

Package Sherlock in a Docker container for consistent deployments.

### Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install sherlock package
RUN pip install -e .

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Create directories
RUN mkdir -p /app/artifacts /app/data

ENV SHERLOCK_ARTIFACTS_PATH=/app/artifacts
ENV SHERLOCK_DB_PATH=/app/data/sherlock.db

ENTRYPOINT ["sherlock"]
CMD ["--help"]
```

### Build and Run

```bash
# Build
docker build -t sherlock:0.1.0 .

# Run
docker run -v $(pwd)/artifacts:/app/artifacts \
           -v $(pwd)/.env:/app/.env \
           sherlock:0.1.0 run --goal "Complete signup"
```

### Publish to Docker Hub

```bash
docker tag sherlock:0.1.0 yourusername/sherlock:0.1.0
docker push yourusername/sherlock:0.1.0
```

---

## Version Management

### Updating Version Number

Edit `pyproject.toml`:
```toml
version = "0.2.0"  # Update this line
```

### Semantic Versioning

Follow semantic versioning (semver):
- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.2.0): New features, backward compatible
- **PATCH** (0.1.1): Bug fixes, backward compatible

Example:
- `0.1.0` → `0.1.1`: Bug fix
- `0.1.1` → `0.2.0`: New feature
- `0.2.0` → `1.0.0`: Breaking API change

---

## Pre-Release Checklist

Before deploying a new version:

- [ ] Update version in `pyproject.toml`
- [ ] Update CHANGELOG.md with changes
- [ ] Run tests: `pytest tests/`
- [ ] Test installation locally from wheel
- [ ] Update README.md if needed
- [ ] Build package: `python -m build`
- [ ] Test on Test PyPI first
- [ ] Create git tag: `git tag -a v0.1.0 -m "Release 0.1.0"`
- [ ] Push to GitHub: `git push && git push --tags`
- [ ] Upload to PyPI: `twine upload dist/*`
- [ ] Create GitHub release with artifacts
- [ ] Verify installation from PyPI

---

## Troubleshooting

### Package Name Already Exists on PyPI

If `sherlock` is taken, choose a different name:
1. Update `name` in `pyproject.toml` to `sherlock-ai-tester` or similar
2. Rebuild and upload

### Missing Dependencies

If users report missing dependencies:
1. Add to `dependencies` in `pyproject.toml`
2. Increment version
3. Rebuild and republish

### Playwright Browsers Not Installing

Remind users to run:
```bash
playwright install
```

Or add post-install hook in `setup.py` (advanced).

### Permission Errors on PyPI Upload

Ensure:
1. API token is correct in `~/.pypirc`
2. Token has correct scope (entire account or specific project)
3. Package name isn't already taken

---

## CI/CD Automation (Optional)

### GitHub Actions for Automatic Publishing

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine

    - name: Build package
      run: python -m build

    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

Add `PYPI_API_TOKEN` to GitHub repository secrets.

---

## Support & Documentation

- **Installation Issues**: Direct users to README.md installation section
- **Usage Questions**: Point to SHERLOCK_CLI_GUIDE.md
- **Bug Reports**: GitHub Issues
- **Feature Requests**: GitHub Discussions

---

## Summary

**For quick distribution:** Use Method 1 (build wheel and share)
**For public release:** Use Method 2 (PyPI)
**For development teams:** Use Method 3 (GitHub install)
**For formal releases:** Use Method 4 (GitHub Releases)
**For containerized deployments:** Use Method 5 (Docker)

Choose the method that best fits your distribution needs!
