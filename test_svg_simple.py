#!/usr/bin/env python3
"""Test simple du module SVG"""

from svg_templates import ICGSSVGTemplates, SVGConfig

# Test basique
config = SVGConfig(width=400, height=300)
templates = ICGSSVGTemplates(config)

print("🧪 Test génération CSS styles...")
try:
    css = templates._get_css_styles()
    print(f"✅ CSS généré: {len(css)} caractères")
    print("Début du CSS:")
    print(css[:200] + "...")
except Exception as e:
    print(f"❌ Erreur CSS: {e}")

print("\n🧪 Test structure SVG de base...")
try:
    svg = templates.get_base_svg_structure("Test")
    print(f"✅ Structure SVG générée: {len(svg)} caractères")

    # Test avec contenu simple
    content = "<circle cx='200' cy='150' r='10' fill='red'/>"
    svg_with_content = templates.get_base_svg_structure("Test", content)
    print(f"✅ SVG avec contenu: {len(svg_with_content)} caractères")

except Exception as e:
    print(f"❌ Erreur structure SVG: {e}")

print("\n🧪 Test cluster secteur simple...")
try:
    agents_test = [
        {'id': 'TEST_01', 'balance': 1000},
        {'id': 'TEST_02', 'balance': 800}
    ]
    cluster = templates.render_sector_cluster('AGRICULTURE', agents_test, 200, 150)
    print(f"✅ Cluster généré: {len(cluster)} caractères")

except Exception as e:
    print(f"❌ Erreur cluster: {e}")