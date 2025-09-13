#!/bin/bash
# ICGS Environment Setup Script
# Configuration environnement développement avec validation

set -e  # Exit sur erreur

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏗️  ICGS Environment Setup${NC}"
echo "================================================"

# 1. Validation Python version
echo -e "${BLUE}📋 Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}✓ Found: $PYTHON_VERSION${NC}"
    
    # Vérification version minimale (3.8+)
    PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
    
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        echo -e "${GREEN}✓ Python version compatible (≥3.8)${NC}"
    else
        echo -e "${RED}❌ Python 3.8+ requis, trouvé $PYTHON_MAJOR.$PYTHON_MINOR${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Python3 non trouvé. Veuillez installer Python 3.8+${NC}"
    exit 1
fi

# 2. Création répertoires nécessaires
echo -e "\n${BLUE}📁 Creating project directories...${NC}"
mkdir -p logs temp benchmark_results
echo -e "${GREEN}✓ Directories created${NC}"

# 3. Chargement variables environnement
echo -e "\n${BLUE}🔧 Loading environment variables...${NC}"
if [ -f .env ]; then
    source .env
    echo -e "${GREEN}✓ Environment variables loaded${NC}"
    echo -e "   ICGS_ROOT: ${ICGS_ROOT}"
    echo -e "   PYTHONPATH: ${PYTHONPATH}"
else
    echo -e "${RED}❌ File .env not found${NC}"
    exit 1
fi

# 4. Installation dépendances si requirements.txt existe
echo -e "\n${BLUE}📦 Checking dependencies...${NC}"
if [ -f requirements.txt ]; then
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    if python3 -m pip install -r requirements.txt > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Dependencies installed${NC}"
    else
        echo -e "${YELLOW}⚠️  Some dependencies may have failed to install${NC}"
        echo -e "   Run manually: python3 -m pip install -r requirements.txt"
    fi
else
    echo -e "${YELLOW}⚠️  requirements.txt not found${NC}"
fi

# 5. Validation structure projet
echo -e "\n${BLUE}🏗️  Validating project structure...${NC}"
REQUIRED_DIRS=("icgs_core" "icgs_simulation" "tests" "examples" "docs")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓ $dir/${NC}"
    else
        echo -e "${RED}❌ Missing: $dir/${NC}"
        exit 1
    fi
done

# 6. Test import modules ICGS
echo -e "\n${BLUE}🐍 Testing Python module imports...${NC}"
if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    import icgs_core
    from icgs_core.account_taxonomy import AccountTaxonomy
    print('✓ Core modules import success')
except Exception as e:
    print(f'❌ Core import failed: {e}')
    sys.exit(1)

try:
    import icgs_simulation
    from icgs_simulation import EconomicSimulation
    print('✓ Simulation modules import success')
except Exception as e:
    print(f'❌ Simulation import failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
    echo -e "${GREEN}✓ All modules importable${NC}"
else
    echo -e "${RED}❌ Module import failed${NC}"
    exit 1
fi

# 7. Génération script activation
echo -e "\n${BLUE}📝 Generating activation script...${NC}"
cat > activate_icgs.sh << 'EOF'
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

icgs_simulation_advanced() {
    echo "🏭 Running advanced economic simulation..."
    python3 icgs_simulation/examples/advanced_simulation.py "$@"
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
EOF

chmod +x activate_icgs.sh
echo -e "${GREEN}✓ Activation script created: activate_icgs.sh${NC}"

# 8. Résumé configuration
echo -e "\n${GREEN}🎉 ICGS Environment Setup Complete!${NC}"
echo "================================================"
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Activate environment: ${YELLOW}source activate_icgs.sh${NC}"
echo "  2. Run tests: ${YELLOW}icgs_test${NC}"
echo "  3. Check status: ${YELLOW}icgs_status${NC}"
echo ""
echo -e "${BLUE}Available commands after activation:${NC}"
echo "  • icgs_test [args]       - Run all tests"
echo "  • icgs_test_academic     - Run academic validation tests"
echo "  • icgs_simulation        - Run simulation demo with Price Discovery"
echo "  • icgs_status           - Show environment status"
echo ""
echo -e "${YELLOW}Note: Run 'source activate_icgs.sh' in each terminal session${NC}"