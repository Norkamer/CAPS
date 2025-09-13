#!/bin/bash
# ICGS Environment Activation Script
# Usage: source activate_icgs.sh

# Load environment variables
if [ -f .env ]; then
    source .env
    echo "🏗️ ICGS environment activated"
    echo "   PYTHONPATH configured for ICGS modules"
    echo "   Ready for development and testing"
else
    echo "❌ .env file not found"
    return 1
fi

# Fonction utilitaires pour développement
icgs_test() {
    echo "🧪 Running ICGS tests with proper environment..."
    python3 -m pytest tests/ -v "$@"
}

icgs_test_academic() {
    echo "🎓 Running academic validation tests..."
    python3 -m pytest tests/test_academic_*.py -v "$@"
}

icgs_simulation() {
    echo "🎯 Running ICGS simulation demo..."
    python3 icgs_simulation/examples/mini_simulation.py "$@"
}

icgs_status() {
    echo "📊 ICGS Environment Status:"
    echo "   Root: $ICGS_ROOT"
    echo "   Python: $(python3 --version)"
    echo "   PYTHONPATH configured: $(echo $PYTHONPATH | grep -q $(pwd) && echo 'YES' || echo 'NO')"
    echo "   Core modules: $(python3 -c 'from icgs_core.account_taxonomy import AccountTaxonomy; print("AVAILABLE")' 2>/dev/null || echo 'NOT AVAILABLE')"
    echo "   Simulation modules: $(python3 -c 'from icgs_simulation import EconomicSimulation; print("AVAILABLE")' 2>/dev/null || echo 'NOT AVAILABLE')"
}

export -f icgs_test icgs_test_academic icgs_simulation icgs_status
