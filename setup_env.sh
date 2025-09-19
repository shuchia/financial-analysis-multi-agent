#!/usr/bin/env bash
set -e

PY_VERSION="3.12.6"

echo "➡️  Uninstalling any previous build of Python $PY_VERSION..."
pyenv uninstall -f $PY_VERSION || true

echo "➡️  Trying to build Python $PY_VERSION with GNU readline..."
if env \
  PYTHON_CONFIGURE_OPTS="--enable-shared --with-readline=readline" \
  CPPFLAGS="-I$(brew --prefix readline)/include" \
  LDFLAGS="-L$(brew --prefix readline)/lib" \
  PKG_CONFIG_PATH="$(brew --prefix readline)/lib/pkgconfig" \
  pyenv install $PY_VERSION; then
  echo "✅ Successfully built Python $PY_VERSION with readline support"
else
  echo "⚠️  Failed to build with readline. Retrying without readline..."
  pyenv uninstall -f $PY_VERSION || true
  env \
    PYTHON_CONFIGURE_OPTS="--enable-shared --without-readline" \
    pyenv install $PY_VERSION
  echo "✅ Successfully built Python $PY_VERSION without readline"
fi

echo "➡️  Setting global Python version..."
pyenv global $PY_VERSION

echo "➡️  Done! Python $(python3 --version) is ready 🎉"

