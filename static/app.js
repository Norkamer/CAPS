/**
 * ICGS 3D Web Application - SPA Navigation avec Three.js
 *
 * Application Single Page avec 5 modules intégrés :
 * 1. Dashboard 3D - Vue d'ensemble économie massive
 * 2. Transaction Navigator - Navigation transactions avec filtres
 * 3. Sector Analysis - Analyse inter-sectorielle clustering 3D
 * 4. Simplex Viewer - Visualisation algorithme Simplex
 * 5. Data Export - Export multi-format
 */

// ======================================
// CONFIGURATION GLOBALE
// ======================================
const ICGS3DApp = {
    // Configuration Three.js
    scene: null,
    camera: null,
    renderer: null,
    controls: null,

    // État application
    currentPage: 'dashboard',
    economyData: null,
    transactionData: null,
    performance3DStats: null,

    // Cache données 3D
    cache3D: new Map(),

    // Configuration couleurs secteurs
    sectorColors: {
        'AGRICULTURE': 0x4CAF50,    // Vert
        'INDUSTRY': 0xFF9800,       // Orange
        'SERVICES': 0x2196F3,       // Bleu
        'FINANCE': 0x9C27B0,        // Violet
        'ENERGY': 0xF44336          // Rouge
    }
};

// ======================================
// CORE APPLICATION FRAMEWORK
// ======================================

class ICGS3DCore {
    constructor() {
        this.initializeApp();
        this.setupEventListeners();
    }

    async initializeApp() {
        console.log('🚀 [DEBUG] Initialisation ICGS 3D Application...');

        // Détection appareil initial
        console.log('📱 [DEBUG] Détection appareil...');
        this.detectDevice();

        // Vérifier support WebGL
        console.log('🖥️ [DEBUG] Vérification WebGL...');
        if (!this.checkWebGLSupport()) {
            console.error('❌ [DEBUG] WebGL non supporté');
            this.showError('WebGL non supporté par ce navigateur');
            return;
        }

        // Initialiser Three.js
        console.log('🎮 [DEBUG] Initialisation Three.js...');
        this.initializeThreeJS();

        // Optimisation initiale selon appareil
        console.log('⚡ [DEBUG] Optimisation performance...');
        this.optimizePerformanceForDevice();

        // Setup contrôles tactiles si mobile
        console.log('👆 [DEBUG] Setup contrôles tactiles...');
        this.setupTouchControls();

        // Setup navigation SPA
        console.log('🧭 [DEBUG] Setup navigation SPA...');
        this.setupSPANavigation();

        // Charger données initiales
        console.log('📡 [DEBUG] Chargement données initiales...');
        await this.loadInitialData();

        // Afficher première page
        console.log('📄 [DEBUG] Navigation vers dashboard...');
        this.navigateToPage('dashboard');

        console.log(`✅ [DEBUG] Application initialisée pour: ${this.getDeviceType()}`);
    }

    detectDevice() {
        const width = window.innerWidth;
        const height = window.innerHeight;
        const isMobile = width <= 768;
        const isTablet = width > 768 && width <= 1024;
        const isDesktop = width > 1024;
        const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

        ICGS3DApp.deviceContext = {
            isMobile,
            isTablet,
            isDesktop,
            isTouch,
            width,
            height,
            pixelRatio: window.devicePixelRatio || 1
        };

        console.log('📱 Appareil détecté:', this.getDeviceType());
    }

    getDeviceType() {
        const { isMobile, isTablet, isDesktop, isTouch } = ICGS3DApp.deviceContext;
        if (isMobile) return isTouch ? 'Mobile tactile' : 'Mobile';
        if (isTablet) return isTouch ? 'Tablet tactile' : 'Tablet';
        if (isDesktop) return isTouch ? 'Desktop tactile' : 'Desktop';
        return 'Inconnu';
    }

    setupTouchControls() {
        const { isMobile, isTablet, isTouch } = ICGS3DApp.deviceContext;

        if (!isTouch) return;

        const container = document.getElementById('three-container');
        if (!container) return;

        // Désactiver le zoom navigateur sur mobile
        if (isMobile) {
            document.addEventListener('touchmove', (e) => {
                if (e.scale && e.scale !== 1) {
                    e.preventDefault();
                }
            }, { passive: false });

            // Gestion multi-touch pour contrôles 3D
            let touchStartDistance = 0;
            let touchStartRotation = 0;

            container.addEventListener('touchstart', (e) => {
                if (e.touches.length === 2) {
                    // Pinch-to-zoom et rotation
                    const touch1 = e.touches[0];
                    const touch2 = e.touches[1];

                    touchStartDistance = Math.hypot(
                        touch2.clientX - touch1.clientX,
                        touch2.clientY - touch1.clientY
                    );

                    touchStartRotation = Math.atan2(
                        touch2.clientY - touch1.clientY,
                        touch2.clientX - touch1.clientX
                    );
                }
            });

            container.addEventListener('touchmove', (e) => {
                if (e.touches.length === 2 && ICGS3DApp.controls) {
                    e.preventDefault();

                    const touch1 = e.touches[0];
                    const touch2 = e.touches[1];

                    // Zoom par pincement
                    const currentDistance = Math.hypot(
                        touch2.clientX - touch1.clientX,
                        touch2.clientY - touch1.clientY
                    );

                    const zoomFactor = currentDistance / touchStartDistance;
                    if (Math.abs(zoomFactor - 1) > 0.1) {
                        const zoomSpeed = isMobile ? 0.02 : 0.05;
                        ICGS3DApp.camera.zoom *= 1 + (zoomFactor - 1) * zoomSpeed;
                        ICGS3DApp.camera.updateProjectionMatrix();
                        touchStartDistance = currentDistance;
                    }
                }
            }, { passive: false });
        }

        // Interface tactile améliorée
        if (isMobile || isTablet) {
            container.style.touchAction = 'none';

            // Feedback haptic sur appareils compatibles
            container.addEventListener('touchstart', () => {
                if (navigator.vibrate) {
                    navigator.vibrate(10); // Vibration courte
                }
            });
        }

        console.log('📱 Contrôles tactiles configurés');
    }

    checkWebGLSupport() {
        try {
            const canvas = document.createElement('canvas');
            return !!(window.WebGLRenderingContext && canvas.getContext('webgl'));
        } catch (e) {
            return false;
        }
    }

    initializeOrbitControls(retryCount = 0) {
        console.log(`🎮 [DEBUG] Tentative d'initialisation OrbitControls (${retryCount + 1}/5)...`);

        if (typeof THREE !== 'undefined' && typeof THREE.OrbitControls !== 'undefined') {
            try {
                ICGS3DApp.controls = new THREE.OrbitControls(
                    ICGS3DApp.camera,
                    ICGS3DApp.renderer.domElement
                );
                ICGS3DApp.controls.enableDamping = true;
                ICGS3DApp.controls.dampingFactor = 0.05;
                ICGS3DApp.controls.screenSpacePanning = false;
                ICGS3DApp.controls.maxPolarAngle = Math.PI / 2;

                console.log('✅ [DEBUG] OrbitControls initialisés avec succès');
                return;
            } catch (error) {
                console.error('❌ [DEBUG] Erreur lors de l\'initialisation OrbitControls:', error);
                ICGS3DApp.controls = null;
            }
        } else {
            console.warn(`⚠️ [DEBUG] THREE.OrbitControls non disponible, retry ${retryCount + 1}/5`);

            if (retryCount < 4) {
                // Retry avec délai progressif
                setTimeout(() => {
                    this.initializeOrbitControls(retryCount + 1);
                }, (retryCount + 1) * 200);
                return;
            }
        }

        // Fallback si OrbitControls échoue définitivement
        console.warn('⚠️ [DEBUG] OrbitControls non disponible, navigation limitée');
        ICGS3DApp.controls = null;
    }

    initializeThreeJS() {
        // Scène principale
        ICGS3DApp.scene = new THREE.Scene();
        ICGS3DApp.scene.background = new THREE.Color(0x0a0a0a); // Fond sombre

        // Caméra perspective
        const container = document.getElementById('three-container');
        const aspect = container.clientWidth / container.clientHeight;
        ICGS3DApp.camera = new THREE.PerspectiveCamera(75, aspect, 0.1, 1000);
        ICGS3DApp.camera.position.set(0, 0, 10);

        // Renderer WebGL
        ICGS3DApp.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true
        });
        ICGS3DApp.renderer.setSize(container.clientWidth, container.clientHeight);
        ICGS3DApp.renderer.shadowMap.enabled = true;
        ICGS3DApp.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        container.appendChild(ICGS3DApp.renderer.domElement);

        // Contrôles OrbitControls pour navigation 3D avec vérification robuste
        this.initializeOrbitControls();

        // Éclairage
        this.setupLighting();

        // Boucle animation
        this.animate();

        console.log('✅ Three.js initialisé');
    }

    setupLighting() {
        // Lumière ambiante
        const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
        ICGS3DApp.scene.add(ambientLight);

        // Lumière directionnelle
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(10, 10, 5);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        ICGS3DApp.scene.add(directionalLight);

        // Point light pour éclairage dynamique
        const pointLight = new THREE.PointLight(0x00ffff, 0.5);
        pointLight.position.set(-10, 10, -10);
        ICGS3DApp.scene.add(pointLight);
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        // Update controls avec garde de protection
        if (ICGS3DApp.controls) {
            ICGS3DApp.controls.update();
        }

        // Render scène
        if (ICGS3DApp.renderer && ICGS3DApp.scene && ICGS3DApp.camera) {
            ICGS3DApp.renderer.render(ICGS3DApp.scene, ICGS3DApp.camera);
        }
    }

    setupEventListeners() {
        // Resize window
        window.addEventListener('resize', () => this.onWindowResize());

        // Navigation menu clicks
        document.querySelectorAll('.nav-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const page = e.target.dataset.page;
                this.navigateToPage(page);
            });
        });

        // Performance monitoring
        this.startPerformanceMonitoring();
    }

    onWindowResize() {
        const container = document.getElementById('three-container');
        const width = container.clientWidth;
        const height = container.clientHeight;

        // Mise à jour caméra et renderer
        ICGS3DApp.camera.aspect = width / height;
        ICGS3DApp.camera.updateProjectionMatrix();
        ICGS3DApp.renderer.setSize(width, height);

        // Adaptation responsive intelligente
        this.adaptToScreenSize(width, height);

        // Recalcul performance selon taille écran
        this.optimizePerformanceForDevice();

        console.log(`📱 Resize adaptatif: ${width}x${height}`);
    }

    adaptToScreenSize(width, height) {
        // Détection type écran et ajustements
        const isMobile = width <= 768;
        const isTablet = width > 768 && width <= 1024;
        const isDesktop = width > 1024;

        // Ajustement contrôles selon type écran
        if (ICGS3DApp.controls) {
            if (isMobile) {
                // Mobile: contrôles tactiles optimisés
                ICGS3DApp.controls.enablePan = true;
                ICGS3DApp.controls.panSpeed = 0.8;
                ICGS3DApp.controls.rotateSpeed = 0.3;
                ICGS3DApp.controls.zoomSpeed = 0.6;
                ICGS3DApp.controls.enableDamping = true;
                ICGS3DApp.controls.dampingFactor = 0.1;
            } else if (isTablet) {
                // Tablet: contrôles hybrides
                ICGS3DApp.controls.enablePan = true;
                ICGS3DApp.controls.panSpeed = 0.6;
                ICGS3DApp.controls.rotateSpeed = 0.4;
                ICGS3DApp.controls.zoomSpeed = 0.8;
                ICGS3DApp.controls.dampingFactor = 0.08;
            } else {
                // Desktop: contrôles précis
                ICGS3DApp.controls.enablePan = true;
                ICGS3DApp.controls.panSpeed = 0.5;
                ICGS3DApp.controls.rotateSpeed = 0.5;
                ICGS3DApp.controls.zoomSpeed = 1.0;
                ICGS3DApp.controls.dampingFactor = 0.05;
            }
        }

        // Ajustement interface utilisateur
        this.updateUIForScreenSize(isMobile, isTablet, isDesktop);
    }

    updateUIForScreenSize(isMobile, isTablet, isDesktop) {
        // Cache contexte écran pour autres méthodes
        ICGS3DApp.deviceContext = { isMobile, isTablet, isDesktop };

        // Ajustement visibilité éléments selon écran
        const pageContent = document.querySelector('.page-content');
        if (pageContent) {
            if (isMobile) {
                // Mobile: collapsible panels
                pageContent.style.transition = 'max-height 0.3s ease';
            }
        }

        // Ajustement contrôles 3D GUI
        this.updateGUIForDevice();
    }

    updateGUIForDevice() {
        // Ajustement dat.GUI selon appareil si présent
        if (window.guiControls) {
            const { isMobile, isTablet } = ICGS3DApp.deviceContext;

            if (isMobile) {
                // Mobile: GUI compacte
                window.guiControls.domElement.style.fontSize = '11px';
                window.guiControls.domElement.style.width = '250px';
            } else if (isTablet) {
                // Tablet: GUI intermédiaire
                window.guiControls.domElement.style.fontSize = '12px';
                window.guiControls.domElement.style.width = '280px';
            } else {
                // Desktop: GUI complète
                window.guiControls.domElement.style.fontSize = '13px';
                window.guiControls.domElement.style.width = '320px';
            }
        }
    }

    optimizePerformanceForDevice() {
        const { isMobile, isTablet, isDesktop } = ICGS3DApp.deviceContext || {};

        if (!ICGS3DApp.renderer) return;

        // Adaptation qualité rendu selon appareil
        if (isMobile) {
            // Mobile: performance privilégiée
            ICGS3DApp.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
            ICGS3DApp.renderer.shadowMap.enabled = false;
            ICGS3DApp.adaptiveParticleCount = 800; // Réduit pour mobile
        } else if (isTablet) {
            // Tablet: équilibre performance/qualité
            ICGS3DApp.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            ICGS3DApp.renderer.shadowMap.enabled = true;
            ICGS3DApp.renderer.shadowMap.type = THREE.BasicShadowMap;
            ICGS3DApp.adaptiveParticleCount = 1500;
        } else {
            // Desktop: qualité maximale
            ICGS3DApp.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2.5));
            ICGS3DApp.renderer.shadowMap.enabled = true;
            ICGS3DApp.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            ICGS3DApp.adaptiveParticleCount = 2000;
        }

        // Notification changement performance
        if (isMobile) {
            this.showNotification('Mode performance mobile activé', 'info');
        } else if (isTablet) {
            this.showNotification('Mode performance tablet activé', 'info');
        }
    }

    async loadInitialData() {
        console.log('🚀 [DEBUG] Démarrage loadInitialData...');
        try {
            // Lancer économie 3D si pas déjà active
            console.log('📡 [DEBUG] Appel API /api/economy/launch_3d...');
            const response = await fetch('/api/economy/launch_3d', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    agents_mode: '65_agents',
                    sectors_config: {
                        'AGRICULTURE': 10,
                        'INDUSTRY': 15,
                        'SERVICES': 20,
                        'FINANCE': 8,
                        'ENERGY': 12
                    },
                    enable_3d_analysis: true,
                    flow_intensity: 0.7
                })
            });

            console.log('📡 [DEBUG] Réponse API:', response.status, response.statusText);

            if (response.ok) {
                ICGS3DApp.economyData = await response.json();
                console.log('✅ [DEBUG] Économie 3D chargée:', ICGS3DApp.economyData);
            } else {
                console.error('❌ [DEBUG] Erreur API launch_3d:', response.status);
                // Utiliser données mock si API non disponible
                console.log('🔧 [DEBUG] Utilisation données mock...');
                ICGS3DApp.economyData = { agents: [], sectors: [], mock: true };
            }

            // Charger statistiques performance
            console.log('📊 [DEBUG] Chargement stats performance...');
            await this.loadPerformanceStats();

        } catch (error) {
            console.error('❌ [DEBUG] Erreur dans loadInitialData:', error);
            this.showNotification('Erreur chargement données', 'error');
            // Fallback en cas d'erreur
            ICGS3DApp.economyData = { agents: [], sectors: [], mock: true };
        }
        console.log('✅ [DEBUG] loadInitialData terminé');
    }

    async loadPerformanceStats() {
        console.log('📊 [DEBUG] Appel /api/performance/stats...');
        try {
            const response = await fetch('/api/performance/stats');
            console.log('📊 [DEBUG] Réponse performance stats:', response.status);
            if (response.ok) {
                ICGS3DApp.performance3DStats = await response.json();
                console.log('✅ [DEBUG] Stats performance chargées:', ICGS3DApp.performance3DStats);
            } else {
                console.warn('⚠️ [DEBUG] Performance stats non OK:', response.status);
                // Mock stats si API non disponible
                ICGS3DApp.performance3DStats = {
                    cache_hit_rate: 0.75,
                    agents_count: 65,
                    transactions_count: 150,
                    mock: true
                };
            }
        } catch (error) {
            console.warn('❌ [DEBUG] Erreur performance stats:', error);
            // Mock stats en cas d'erreur
            ICGS3DApp.performance3DStats = {
                cache_hit_rate: 0.75,
                agents_count: 65,
                transactions_count: 150,
                mock: true
            };
        }
        console.log('✅ [DEBUG] loadPerformanceStats terminé');
    }

    setupSPANavigation() {
        // Masquer toutes les pages initialement
        document.querySelectorAll('.page-content').forEach(page => {
            page.style.display = 'none';
        });
    }

    navigateToPage(pageName) {
        // Désactiver bouton nav précédent
        document.querySelectorAll('.nav-button').forEach(btn => {
            btn.classList.remove('active');
        });

        // Masquer toutes les pages
        document.querySelectorAll('.page-content').forEach(page => {
            page.style.display = 'none';
        });

        // Activer nouveau bouton
        const activeButton = document.querySelector(`[data-page="${pageName}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
        }

        // Afficher page cible
        const targetPage = document.getElementById(`${pageName}-page`);
        if (targetPage) {
            targetPage.style.display = 'block';
        }

        // Mettre à jour état
        ICGS3DApp.currentPage = pageName;

        // Charger contenu spécifique à la page
        this.loadPageContent(pageName);

        console.log(`📄 Navigation vers: ${pageName}`);
    }

    async loadPageContent(pageName) {
        // Vider scène 3D précédente
        this.clearScene3D();

        switch (pageName) {
            case 'dashboard':
                await this.loadDashboardContent();
                break;
            case 'transactions':
                await this.loadTransactionNavigator();
                break;
            case 'sectors':
                await this.loadSectorAnalysis();
                break;
            case 'simplex':
                await this.loadSimplexViewer();
                break;
            case 'export':
                await this.loadDataExport();
                break;
        }
    }

    clearScene3D() {
        // Nettoyer objets 3D existants (sauf lumières)
        const objectsToRemove = [];
        ICGS3DApp.scene.traverse(child => {
            if (child.isMesh) {
                objectsToRemove.push(child);
            }
        });

        objectsToRemove.forEach(obj => {
            ICGS3DApp.scene.remove(obj);
            if (obj.geometry) obj.geometry.dispose();
            if (obj.material) obj.material.dispose();
        });
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()">×</button>
        `;

        document.body.appendChild(notification);

        // Auto-remove après 5s
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    showError(message) {
        const errorContainer = document.getElementById('error-container');
        errorContainer.innerHTML = `
            <div class="error-message">
                <h3>❌ Erreur</h3>
                <p>${message}</p>
                <button onclick="location.reload()">Recharger</button>
            </div>
        `;
        errorContainer.style.display = 'block';
    }

    startPerformanceMonitoring() {
        setInterval(async () => {
            if (ICGS3DApp.currentPage === 'dashboard') {
                await this.updatePerformanceMetrics();
            }
        }, 5000); // Mise à jour toutes les 5s
    }

    async updatePerformanceMetrics() {
        try {
            const response = await fetch('/api/performance/stats');
            if (response.ok) {
                const stats = await response.json();
                ICGS3DApp.performance3DStats = stats;
                this.refreshDashboardMetrics(stats);
            }
        } catch (error) {
            console.warn('Erreur mise à jour performance:', error);
        }
    }

    refreshDashboardMetrics(stats) {
        const metricsContainer = document.querySelector('#dashboard-metrics');
        if (metricsContainer && stats.performance_stats) {
            const cache = stats.performance_stats.cache_performance;
            const simulation = stats.performance_stats.simulation;

            metricsContainer.innerHTML = `
                <div class="metric-card">
                    <h4>Cache Performance</h4>
                    <p>Hit Rate: ${cache.hit_rate_percent}%</p>
                    <p>Hits: ${cache.hit_count}</p>
                </div>
                <div class="metric-card">
                    <h4>Simulation</h4>
                    <p>Agents: ${simulation.agents_count}</p>
                    <p>Transactions: ${simulation.transactions_count}</p>
                </div>
            `;
        }
    }
}

// ======================================
// PAGE MODULES
// ======================================

// Dashboard 3D - Vue d'ensemble économie massive
ICGS3DCore.prototype.loadDashboardContent = async function() {
    console.log('📊 [DEBUG] Démarrage loadDashboardContent...');

    console.log('🔍 [DEBUG] État economyData:', !!ICGS3DApp.economyData);
    if (!ICGS3DApp.economyData) {
        console.warn('⚠️ [DEBUG] Pas de données économie - affichage notification');
        this.showNotification('Chargement données économie...', 'info');
        return;
    }

    console.log('✅ [DEBUG] Données économie disponibles:', ICGS3DApp.economyData);

    // Créer visualisation 3D massive des secteurs avec animations
    console.log('🎨 [DEBUG] Création visualisation 3D massive...');
    await this.create3DMassiveVisualization();

    // Créer système particules pour flux économiques
    console.log('✨ [DEBUG] Création système particules...');
    this.createParticleSystem();

    // Initialiser contrôles avancés
    console.log('🎮 [DEBUG] Initialisation contrôles avancés...');
    this.initializeAdvancedControls();

    // Mettre à jour métriques
    console.log('📊 [DEBUG] État performance3DStats:', !!ICGS3DApp.performance3DStats);
    if (ICGS3DApp.performance3DStats) {
        console.log('📊 [DEBUG] Rafraîchissement métriques dashboard...');
        this.refreshDashboardMetrics(ICGS3DApp.performance3DStats);
    } else {
        console.warn('⚠️ [DEBUG] Pas de stats performance disponibles');
    }

    console.log('✅ [DEBUG] loadDashboardContent terminé');
};

ICGS3DCore.prototype.create3DMassiveVisualization = async function() {
    console.log('🎨 Création visualisation massive 3D...');

    // Configuration géométrique massive pour 65 agents
    const sectors = Object.keys(ICGS3DApp.sectorColors);
    const agentCounts = {
        'AGRICULTURE': 10,
        'INDUSTRY': 15,
        'SERVICES': 20,
        'FINANCE': 8,
        'ENERGY': 12
    };

    // Créer galaxie de secteurs en 3D
    let agentIndex = 0;
    ICGS3DApp.agentMeshes = [];

    sectors.forEach((sector, sectorIndex) => {
        const sectorAngle = (sectorIndex / sectors.length) * Math.PI * 2;
        const sectorRadius = 8 + sectorIndex * 2;

        // Position centrale du secteur
        const sectorX = Math.cos(sectorAngle) * sectorRadius;
        const sectorZ = Math.sin(sectorAngle) * sectorRadius;

        // Créer constellation d'agents par secteur
        const agentCount = agentCounts[sector] || 5;

        for (let i = 0; i < agentCount; i++) {
            const agentAngle = (i / agentCount) * Math.PI * 2;
            const agentRadius = 2 + Math.random() * 1.5;

            // Position relative dans le secteur
            const agentX = sectorX + Math.cos(agentAngle) * agentRadius;
            const agentY = (Math.random() - 0.5) * 3; // Hauteur variable
            const agentZ = sectorZ + Math.sin(agentAngle) * agentRadius;

            // Géométrie agent avec variation de taille
            const size = 0.15 + Math.random() * 0.1;
            const geometry = new THREE.OctahedronGeometry(size, 1);

            // Matériau avec émission pour effet lumineux
            const material = new THREE.MeshPhongMaterial({
                color: ICGS3DApp.sectorColors[sector],
                emissive: ICGS3DApp.sectorColors[sector],
                emissiveIntensity: 0.3,
                transparent: true,
                opacity: 0.8
            });

            const agentMesh = new THREE.Mesh(geometry, material);
            agentMesh.position.set(agentX, agentY, agentZ);

            // Données agent
            agentMesh.userData = {
                id: `${sector}_${i.toString().padStart(2, '0')}`,
                sector: sector,
                type: 'agent',
                index: agentIndex++,
                originalPosition: new THREE.Vector3(agentX, agentY, agentZ),
                animationPhase: Math.random() * Math.PI * 2
            };

            ICGS3DApp.scene.add(agentMesh);
            ICGS3DApp.agentMeshes.push(agentMesh);
        }

        // Label secteur central avec échelle
        this.addEnhancedSectorLabel(sector, sectorX, 3, sectorZ, agentCount);
    });

    // Créer connexions dynamiques entre secteurs
    await this.createDynamicConnections();

    // Démarrer animations
    this.startAgentAnimations();
};

ICGS3DCore.prototype.addTextLabel = function(text, x, y, z) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 256;
    canvas.height = 64;

    context.fillStyle = '#ffffff';
    context.font = '24px Arial';
    context.textAlign = 'center';
    context.fillText(text, 128, 32);

    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({ map: texture });
    const sprite = new THREE.Sprite(material);
    sprite.position.set(x, y, z);
    sprite.scale.set(2, 0.5, 1);

    ICGS3DApp.scene.add(sprite);
};

ICGS3DCore.prototype.createParticleSystem = function() {
    console.log('✨ Création système particules flux économiques...');

    // Géométrie particules adaptative selon appareil
    const particlesCount = ICGS3DApp.adaptiveParticleCount || 2000;
    console.log(`📱 Particules adaptées: ${particlesCount} pour ${this.getDeviceType()}`);
    const positions = new Float32Array(particlesCount * 3);
    const velocities = new Float32Array(particlesCount * 3);
    const colors = new Float32Array(particlesCount * 3);

    // Initialiser particules
    for (let i = 0; i < particlesCount; i++) {
        const i3 = i * 3;

        // Positions aléatoires dans sphère
        const radius = 15 + Math.random() * 5;
        const phi = Math.random() * Math.PI * 2;
        const theta = Math.random() * Math.PI;

        positions[i3] = radius * Math.sin(theta) * Math.cos(phi);
        positions[i3 + 1] = radius * Math.sin(theta) * Math.sin(phi);
        positions[i3 + 2] = radius * Math.cos(theta);

        // Vitesses orbitales
        velocities[i3] = (Math.random() - 0.5) * 0.02;
        velocities[i3 + 1] = (Math.random() - 0.5) * 0.02;
        velocities[i3 + 2] = (Math.random() - 0.5) * 0.02;

        // Couleurs dynamiques
        const color = new THREE.Color();
        color.setHSL(Math.random(), 0.7, 0.6);
        colors[i3] = color.r;
        colors[i3 + 1] = color.g;
        colors[i3 + 2] = color.b;
    }

    // Géométrie et matériau particules
    const particlesGeometry = new THREE.BufferGeometry();
    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particlesGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const particlesMaterial = new THREE.PointsMaterial({
        size: 0.05,
        vertexColors: true,
        transparent: true,
        opacity: 0.6,
        blending: THREE.AdditiveBlending
    });

    ICGS3DApp.particleSystem = new THREE.Points(particlesGeometry, particlesMaterial);
    ICGS3DApp.particleVelocities = velocities;

    ICGS3DApp.scene.add(ICGS3DApp.particleSystem);
};

ICGS3DCore.prototype.createDynamicConnections = async function() {
    console.log('🔗 Création connexions dynamiques inter-sectorielles...');

    if (!ICGS3DApp.agentMeshes || ICGS3DApp.agentMeshes.length < 2) {
        return;
    }

    ICGS3DApp.connections = [];
    const connectionCount = Math.min(50, ICGS3DApp.agentMeshes.length * 2);

    for (let i = 0; i < connectionCount; i++) {
        // Sélectionner agents aléatoirement pour connexions
        const agent1 = ICGS3DApp.agentMeshes[Math.floor(Math.random() * ICGS3DApp.agentMeshes.length)];
        const agent2 = ICGS3DApp.agentMeshes[Math.floor(Math.random() * ICGS3DApp.agentMeshes.length)];

        if (agent1.userData.sector !== agent2.userData.sector) {
            // Créer ligne de connexion inter-sectorielle
            const lineGeometry = new THREE.BufferGeometry().setFromPoints([
                agent1.position,
                agent2.position
            ]);

            const lineMaterial = new THREE.LineBasicMaterial({
                color: 0x00ffff,
                transparent: true,
                opacity: 0.3
            });

            const line = new THREE.Line(lineGeometry, lineMaterial);
            line.userData = {
                type: 'connection',
                agent1: agent1,
                agent2: agent2,
                animationOffset: Math.random() * Math.PI * 2
            };

            ICGS3DApp.scene.add(line);
            ICGS3DApp.connections.push(line);
        }
    }
};

ICGS3DCore.prototype.startAgentAnimations = function() {
    console.log('🎬 Démarrage animations agents...');

    if (ICGS3DApp.animationRunning) return;
    ICGS3DApp.animationRunning = true;

    const animateAgents = () => {
        if (!ICGS3DApp.animationRunning) return;

        const time = Date.now() * 0.001;

        // Animer agents avec mouvement organique
        ICGS3DApp.agentMeshes.forEach(agent => {
            const userData = agent.userData;
            const phase = userData.animationPhase + time * 0.5;

            // Oscillation subtile autour position originale
            const offset = Math.sin(phase) * 0.2;
            agent.position.y = userData.originalPosition.y + offset;

            // Rotation lente
            agent.rotation.x += 0.01;
            agent.rotation.y += 0.005;

            // Pulsation émissive basée sur activité
            if (agent.material) {
                agent.material.emissiveIntensity = 0.2 + Math.sin(phase * 2) * 0.1;
            }
        });

        // Animer connexions
        ICGS3DApp.connections.forEach(connection => {
            const opacity = 0.2 + Math.sin(time * 2 + connection.userData.animationOffset) * 0.1;
            connection.material.opacity = Math.max(0.1, opacity);
        });

        // Animer système particules
        if (ICGS3DApp.particleSystem) {
            const positions = ICGS3DApp.particleSystem.geometry.attributes.position.array;
            const velocities = ICGS3DApp.particleVelocities;

            for (let i = 0; i < positions.length; i += 3) {
                // Mouvement orbital des particules
                positions[i] += velocities[i];
                positions[i + 1] += velocities[i + 1];
                positions[i + 2] += velocities[i + 2];

                // Contrainte sphérique
                const distance = Math.sqrt(
                    positions[i] ** 2 +
                    positions[i + 1] ** 2 +
                    positions[i + 2] ** 2
                );

                if (distance > 20 || distance < 10) {
                    // Réinitialiser particule
                    const radius = 15;
                    const phi = Math.random() * Math.PI * 2;
                    const theta = Math.random() * Math.PI;

                    positions[i] = radius * Math.sin(theta) * Math.cos(phi);
                    positions[i + 1] = radius * Math.sin(theta) * Math.sin(phi);
                    positions[i + 2] = radius * Math.cos(theta);
                }
            }

            ICGS3DApp.particleSystem.geometry.attributes.position.needsUpdate = true;
        }

        requestAnimationFrame(animateAgents);
    };

    animateAgents();
};

ICGS3DCore.prototype.initializeAdvancedControls = function() {
    console.log('🎛️ Initialisation contrôles avancés...');

    // Configuration dat.GUI pour contrôles temps réel
    ICGS3DApp.gui = new dat.GUI({ autoPlace: false });

    // Container GUI
    const guiContainer = document.createElement('div');
    guiContainer.style.position = 'absolute';
    guiContainer.style.top = '20px';
    guiContainer.style.right = '380px'; // À côté du panneau
    guiContainer.style.zIndex = '1000';
    guiContainer.appendChild(ICGS3DApp.gui.domElement);
    document.body.appendChild(guiContainer);

    // Paramètres contrôlables
    const params = {
        agentAnimation: true,
        particleSystem: true,
        connections: true,
        animationSpeed: 1.0,
        particleCount: 2000,
        emissiveIntensity: 0.3,
        connectionOpacity: 0.3,
        autoRotate: false,
        resetView: () => this.resetCameraView()
    };

    ICGS3DApp.guiParams = params;

    // Interface contrôles
    const animationFolder = ICGS3DApp.gui.addFolder('Animations');
    animationFolder.add(params, 'agentAnimation').onChange(value => {
        ICGS3DApp.animationRunning = value;
        if (value) this.startAgentAnimations();
    });
    animationFolder.add(params, 'animationSpeed', 0.1, 3.0);
    animationFolder.add(params, 'autoRotate').onChange(value => {
        ICGS3DApp.controls.autoRotate = value;
    });

    const visualFolder = ICGS3DApp.gui.addFolder('Visualisation');
    visualFolder.add(params, 'particleSystem').onChange(value => {
        if (ICGS3DApp.particleSystem) {
            ICGS3DApp.particleSystem.visible = value;
        }
    });
    visualFolder.add(params, 'connections').onChange(value => {
        ICGS3DApp.connections.forEach(conn => {
            conn.visible = value;
        });
    });
    visualFolder.add(params, 'emissiveIntensity', 0, 1).onChange(value => {
        ICGS3DApp.agentMeshes.forEach(agent => {
            if (agent.material) {
                agent.material.emissiveIntensity = value;
            }
        });
    });

    const controlFolder = ICGS3DApp.gui.addFolder('Contrôles');
    controlFolder.add(params, 'resetView');

    // Ouvrir dossiers par défaut
    animationFolder.open();
    visualFolder.open();
};

ICGS3DCore.prototype.resetCameraView = function() {
    ICGS3DApp.camera.position.set(0, 0, 25);
    if (ICGS3DApp.controls) {
        ICGS3DApp.controls.target.set(0, 0, 0);
        ICGS3DApp.controls.update();
    }
};

ICGS3DCore.prototype.addEnhancedSectorLabel = function(text, x, y, z, agentCount) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 512;
    canvas.height = 128;

    // Fond avec gradient
    const gradient = context.createLinearGradient(0, 0, 512, 0);
    gradient.addColorStop(0, 'rgba(0, 255, 255, 0.8)');
    gradient.addColorStop(1, 'rgba(255, 0, 255, 0.8)');
    context.fillStyle = gradient;
    context.fillRect(0, 0, 512, 128);

    // Texte principal
    context.fillStyle = '#ffffff';
    context.font = 'bold 32px Arial';
    context.textAlign = 'center';
    context.fillText(text, 256, 50);

    // Sous-texte avec nombre agents
    context.font = '20px Arial';
    context.fillText(`${agentCount} agents`, 256, 80);

    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(material);
    sprite.position.set(x, y, z);
    sprite.scale.set(4, 1, 1);

    ICGS3DApp.scene.add(sprite);
};

// Transaction Navigator
ICGS3DCore.prototype.loadTransactionNavigator = async function() {
    console.log('💰 Chargement Transaction Navigator...');

    try {
        const response = await fetch('/api/transactions/3d?page=1&per_page=20');
        const data = await response.json();

        if (data.success) {
            ICGS3DApp.transactionData = data;
            await this.create3DTransactionView(data.transactions);
            this.updateTransactionList(data.transactions);
        }
    } catch (error) {
        console.error('Erreur chargement transactions:', error);
    }
};

ICGS3DCore.prototype.create3DTransactionView = async function(transactions) {
    // Visualisation 3D des flux de transactions
    transactions.slice(0, 10).forEach((tx, index) => {
        // Créer point transaction
        const geometry = new THREE.BoxGeometry(0.2, 0.2, 0.2);
        const color = tx.feasible ? 0x00ff00 : 0xff0000;
        const material = new THREE.MeshLambertMaterial({ color });

        const cube = new THREE.Mesh(geometry, material);
        cube.position.set(
            (Math.random() - 0.5) * 10,
            (Math.random() - 0.5) * 10,
            (Math.random() - 0.5) * 10
        );
        cube.userData = { transaction: tx, type: 'transaction' };

        ICGS3DApp.scene.add(cube);
    });
};

ICGS3DCore.prototype.updateTransactionList = function(transactions) {
    const listContainer = document.querySelector('#transaction-list');
    if (listContainer) {
        listContainer.innerHTML = transactions.map(tx => `
            <div class="transaction-item ${tx.feasible ? 'feasible' : 'infeasible'}">
                <strong>${tx.transaction_id}</strong><br>
                ${tx.source_account_id} → ${tx.target_account_id}<br>
                Amount: ${tx.amount}
            </div>
        `).join('');
    }
};

// Stubs pour autres modules
ICGS3DCore.prototype.loadSectorAnalysis = async function() {
    console.log('🏭 Chargement Sector Analysis avec clustering 3D...');

    // Nettoyer scène pour analyse sectorielle
    this.clearScene3D();

    // Charger données agents avec positions
    const agentsData = await this.loadAgentsPositionalData();

    // Créer clustering 3D par secteur
    await this.create3DSectorClustering(agentsData);

    // Mettre à jour interface analyse sectorielle
    this.updateSectorAnalysisInterface(agentsData);

    console.log('✅ Sector Analysis chargé avec clustering');
};

ICGS3DCore.prototype.loadAgentsPositionalData = async function() {
    try {
        // Récupérer données agents avec coordonnées 3D
        const response = await fetch('/api/economy/agents_positions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agents_mode: '65_agents',
                include_coordinates: true,
                clustering_enabled: true
            })
        });

        if (response.ok) {
            const data = await response.json();
            console.log('📊 Données agents positionnelles récupérées:', data);
            return data;
        } else {
            // Données simulées pour clustering
            return this.generateMockAgentsPositionalData();
        }
    } catch (error) {
        console.warn('Utilisation données agents simulées:', error);
        return this.generateMockAgentsPositionalData();
    }
};

ICGS3DCore.prototype.generateMockAgentsPositionalData = function() {
    const sectors = Object.keys(ICGS3DApp.sectorColors);
    const agentCounts = {
        'AGRICULTURE': 10,
        'INDUSTRY': 15,
        'SERVICES': 20,
        'FINANCE': 8,
        'ENERGY': 12
    };

    const agentsData = {
        agents: [],
        sectors_summary: {},
        clustering_stats: {}
    };

    let agentId = 0;

    // Générer agents avec positions par secteur
    sectors.forEach(sector => {
        const count = agentCounts[sector] || 5;
        const sectorAgents = [];

        // Centre de cluster pour ce secteur
        const clusterCenter = this.getSectorClusterCenter(sector);

        for (let i = 0; i < count; i++) {
            // Position dans cluster avec dispersion
            const dispersion = 3;
            const agent = {
                id: `${sector}_${i.toString().padStart(2, '0')}`,
                sector: sector,
                position: {
                    x: clusterCenter.x + (Math.random() - 0.5) * dispersion,
                    y: clusterCenter.y + (Math.random() - 0.5) * dispersion,
                    z: clusterCenter.z + (Math.random() - 0.5) * dispersion
                },
                balance: 1000 + Math.random() * 500,
                connections: Math.floor(Math.random() * 5) + 2,
                activity_level: Math.random()
            };

            sectorAgents.push(agent);
            agentsData.agents.push(agent);
            agentId++;
        }

        agentsData.sectors_summary[sector] = {
            count: count,
            center: clusterCenter,
            agents: sectorAgents
        };
    });

    return agentsData;
};

ICGS3DCore.prototype.getSectorClusterCenter = function(sector) {
    // Positions prédéfinies pour chaque secteur dans l'espace 3D
    const sectorCenters = {
        'AGRICULTURE': { x: -8, y: 0, z: -8 },
        'INDUSTRY': { x: 8, y: 0, z: -8 },
        'SERVICES': { x: 0, y: 8, z: 0 },
        'FINANCE': { x: -8, y: 0, z: 8 },
        'ENERGY': { x: 8, y: 0, z: 8 }
    };

    return sectorCenters[sector] || { x: 0, y: 0, z: 0 };
};

ICGS3DCore.prototype.create3DSectorClustering = async function(agentsData) {
    console.log('🎯 Création clustering secteurs 3D...');

    // Configuration clustering
    ICGS3DApp.sectorClustering = {
        clusters: {},
        agents: agentsData.agents,
        clusteringMethod: 'spatial_distance',
        showConnections: true,
        showBoundaries: true,
        animationSpeed: 1.0
    };

    // Créer clusters visuels par secteur
    const sectors = Object.keys(ICGS3DApp.sectorColors);

    for (const sector of sectors) {
        const sectorData = agentsData.sectors_summary[sector];
        if (sectorData) {
            await this.createSectorCluster(sector, sectorData);
        }
    }

    // Créer connexions inter-sectorielles
    this.createInterSectorConnections(agentsData);

    // Créer limites de clusters
    this.createClusterBoundaries(agentsData);

    // Créer contrôles clustering
    this.createClusteringControls();

    // Animation clustering
    this.animateClusteringEffects();
};

ICGS3DCore.prototype.createSectorCluster = function(sector, sectorData) {
    console.log(`🎨 Création cluster ${sector}...`);

    const color = ICGS3DApp.sectorColors[sector];
    const agents = sectorData.agents;

    // Créer groupe pour le cluster
    const clusterGroup = new THREE.Group();
    clusterGroup.name = `cluster_${sector}`;

    // Créer agents visuels
    agents.forEach((agent, index) => {
        const agentMesh = this.createAgentMesh(agent, color);
        agentMesh.name = `agent_${agent.id}`;
        clusterGroup.add(agentMesh);
    });

    // Centre de cluster
    const centerMesh = this.createClusterCenter(sector, sectorData.center, color);
    centerMesh.name = `center_${sector}`;
    clusterGroup.add(centerMesh);

    // Ajouter à la scène
    ICGS3DApp.scene.add(clusterGroup);

    // Stocker référence cluster
    ICGS3DApp.sectorClustering.clusters[sector] = {
        group: clusterGroup,
        center: sectorData.center,
        agents: agents,
        visible: true
    };
};

ICGS3DCore.prototype.createAgentMesh = function(agent, color) {
    // Géométrie agent selon son activité
    const activity = agent.activity_level;
    const size = 0.1 + activity * 0.15;

    let geometry;
    if (activity > 0.7) {
        geometry = new THREE.SphereGeometry(size, 12, 12);
    } else if (activity > 0.4) {
        geometry = new THREE.BoxGeometry(size, size, size);
    } else {
        geometry = new THREE.ConeGeometry(size, size * 1.5, 8);
    }

    // Matériau avec intensité selon balance
    const intensity = Math.min(agent.balance / 1500, 1);
    const material = new THREE.MeshLambertMaterial({
        color: color,
        emissive: new THREE.Color(color).multiplyScalar(intensity * 0.3),
        transparent: true,
        opacity: 0.8 + intensity * 0.2
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(agent.position.x, agent.position.y, agent.position.z);

    // Données agent
    mesh.userData = {
        agent: agent,
        originalColor: color,
        originalPosition: mesh.position.clone()
    };

    return mesh;
};

ICGS3DCore.prototype.createClusterCenter = function(sector, center, color) {
    // Icône secteur au centre
    const geometry = new THREE.OctahedronGeometry(0.3);
    const material = new THREE.MeshLambertMaterial({
        color: color,
        emissive: new THREE.Color(color).multiplyScalar(0.5),
        wireframe: true
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(center.x, center.y, center.z);

    // Label secteur
    const label = this.createSectorLabel(sector, center);
    mesh.add(label);

    return mesh;
};

ICGS3DCore.prototype.createSectorLabel = function(sector, position) {
    // Canvas pour texte
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 256;
    canvas.height = 64;

    // Style texte
    context.fillStyle = '#000000';
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = '#ffffff';
    context.font = 'bold 18px Arial';
    context.textAlign = 'center';
    context.fillText(sector, canvas.width / 2, canvas.height / 2 + 6);

    // Texture et matériau
    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.MeshBasicMaterial({
        map: texture,
        transparent: true,
        alphaTest: 0.5
    });

    const geometry = new THREE.PlaneGeometry(2, 0.5);
    const label = new THREE.Mesh(geometry, material);
    label.position.y = 0.5;

    return label;
};

ICGS3DCore.prototype.createInterSectorConnections = function(agentsData) {
    console.log('🔗 Création connexions inter-sectorielles...');

    const connectionGroup = new THREE.Group();
    connectionGroup.name = 'inter_sector_connections';

    // Connexions entre centres de clusters
    const sectors = Object.keys(ICGS3DApp.sectorColors);
    for (let i = 0; i < sectors.length; i++) {
        for (let j = i + 1; j < sectors.length; j++) {
            const sectorA = sectors[i];
            const sectorB = sectors[j];

            const centerA = agentsData.sectors_summary[sectorA].center;
            const centerB = agentsData.sectors_summary[sectorB].center;

            const connection = this.createConnectionLine(centerA, centerB, 0x888888);
            connectionGroup.add(connection);
        }
    }

    // Connexions agents aléatoires inter-secteurs
    const agents = agentsData.agents;
    for (let i = 0; i < 20; i++) { // 20 connexions aléatoires
        const agentA = agents[Math.floor(Math.random() * agents.length)];
        const agentB = agents[Math.floor(Math.random() * agents.length)];

        if (agentA.sector !== agentB.sector) {
            const connection = this.createConnectionLine(
                agentA.position, agentB.position, 0x444444, 0.3
            );
            connectionGroup.add(connection);
        }
    }

    ICGS3DApp.scene.add(connectionGroup);
    ICGS3DApp.sectorClustering.connectionsGroup = connectionGroup;
};

ICGS3DCore.prototype.createConnectionLine = function(posA, posB, color = 0xffffff, opacity = 0.6) {
    const points = [
        new THREE.Vector3(posA.x, posA.y, posA.z),
        new THREE.Vector3(posB.x, posB.y, posB.z)
    ];

    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const material = new THREE.LineBasicMaterial({
        color: color,
        transparent: true,
        opacity: opacity
    });

    return new THREE.Line(geometry, material);
};

ICGS3DCore.prototype.createClusterBoundaries = function(agentsData) {
    console.log('📦 Création limites clusters...');

    const boundariesGroup = new THREE.Group();
    boundariesGroup.name = 'cluster_boundaries';

    Object.keys(agentsData.sectors_summary).forEach(sector => {
        const sectorData = agentsData.sectors_summary[sector];
        const boundary = this.createSectorBoundary(sector, sectorData);
        boundariesGroup.add(boundary);
    });

    ICGS3DApp.scene.add(boundariesGroup);
    ICGS3DApp.sectorClustering.boundariesGroup = boundariesGroup;
};

ICGS3DCore.prototype.createSectorBoundary = function(sector, sectorData) {
    const color = ICGS3DApp.sectorColors[sector];
    const center = sectorData.center;
    const agents = sectorData.agents;

    // Calculer rayon englobant pour tous les agents du secteur
    let maxDistance = 0;
    agents.forEach(agent => {
        const distance = Math.sqrt(
            Math.pow(agent.position.x - center.x, 2) +
            Math.pow(agent.position.y - center.y, 2) +
            Math.pow(agent.position.z - center.z, 2)
        );
        maxDistance = Math.max(maxDistance, distance);
    });

    // Sphère de délimitation
    const radius = maxDistance + 1; // Marge
    const geometry = new THREE.SphereGeometry(radius, 16, 16);
    const material = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.1,
        wireframe: true
    });

    const boundary = new THREE.Mesh(geometry, material);
    boundary.position.set(center.x, center.y, center.z);
    boundary.name = `boundary_${sector}`;

    return boundary;
};

ICGS3DCore.prototype.createClusteringControls = function() {
    console.log('🎮 Création contrôles clustering...');

    // Créer dat.GUI pour clustering
    if (window.dat) {
        // Supprimer GUI existant
        if (window.clusteringGUI) {
            window.clusteringGUI.destroy();
        }

        window.clusteringGUI = new dat.GUI({ name: 'Contrôles Clustering' });

        const controls = {
            showConnections: true,
            showBoundaries: true,
            animationSpeed: 1.0,
            clusteringMethod: 'spatial_distance',
            reshuffleClusters: () => this.reshuffleClusters(),
            resetPositions: () => this.resetAgentPositions(),
            toggleSector: (sector) => this.toggleSectorVisibility(sector)
        };

        // Contrôles affichage
        const displayFolder = window.clusteringGUI.addFolder('Affichage');
        displayFolder.add(controls, 'showConnections').name('Connexions').onChange(show => {
            this.toggleConnectionsVisibility(show);
        });
        displayFolder.add(controls, 'showBoundaries').name('Limites clusters').onChange(show => {
            this.toggleBoundariesVisibility(show);
        });

        // Contrôles animation
        const animationFolder = window.clusteringGUI.addFolder('Animation');
        animationFolder.add(controls, 'animationSpeed', 0.1, 3.0).name('Vitesse').onChange(speed => {
            ICGS3DApp.sectorClustering.animationSpeed = speed;
        });

        // Contrôles clustering
        const clusteringFolder = window.clusteringGUI.addFolder('Clustering');
        clusteringFolder.add(controls, 'clusteringMethod', ['spatial_distance', 'economic_activity', 'balance_based']).name('Méthode').onChange(method => {
            this.updateClusteringMethod(method);
        });
        clusteringFolder.add(controls, 'reshuffleClusters').name('🔄 Réorganiser');
        clusteringFolder.add(controls, 'resetPositions').name('🏠 Positions initiales');

        // Contrôles par secteur
        const sectorsFolder = window.clusteringGUI.addFolder('Secteurs');
        Object.keys(ICGS3DApp.sectorColors).forEach(sector => {
            sectorsFolder.add({ [sector]: true }, sector).onChange(visible => {
                this.toggleSectorVisibility(sector, visible);
            });
        });

        displayFolder.open();
        animationFolder.open();
        clusteringFolder.open();
        sectorsFolder.open();

        // Stocker référence
        ICGS3DApp.clusteringControls = controls;
    }
};

ICGS3DCore.prototype.updateSectorAnalysisInterface = function(agentsData) {
    console.log('🖥️ Mise à jour interface Sector Analysis...');

    const pageContent = document.querySelector('.page-content');
    if (pageContent) {
        // Calculer statistiques clustering
        const totalAgents = agentsData.agents.length;
        const sectorsCount = Object.keys(agentsData.sectors_summary).length;

        pageContent.innerHTML = `
            <div class="page-header">
                <h2 class="page-title">Sector Analysis</h2>
                <p class="page-subtitle">Clustering 3D par coordonnées</p>
            </div>

            <div class="controls-section">
                <h4>Statistiques Clustering</h4>
                <div id="clustering-stats">
                    <p><strong>Agents totaux:</strong> ${totalAgents}</p>
                    <p><strong>Secteurs:</strong> ${sectorsCount}</p>
                    <p><strong>Méthode:</strong> <span id="clustering-method">spatial_distance</span></p>
                </div>
            </div>

            <div class="controls-section">
                <h4>Distribution Sectorielle</h4>
                <div id="sectors-distribution">
                    ${this.generateSectorsDistributionHTML(agentsData.sectors_summary)}
                </div>
            </div>

            <div class="controls-section">
                <h4>Analyse Spatiale</h4>
                <div id="spatial-analysis">
                    <p><strong>Dispersion moyenne:</strong> <span id="avg-dispersion">-</span></p>
                    <p><strong>Distance inter-clusters:</strong> <span id="inter-cluster-distance">-</span></p>
                    <p><strong>Densité clustering:</strong> <span id="clustering-density">-</span></p>
                </div>
            </div>

            <div class="controls-section">
                <h4>Contrôles Rapides</h4>
                <button class="btn" onclick="icgs3dApp.reshuffleClusters()">🔄 Réorganiser</button>
                <button class="btn btn-secondary" onclick="icgs3dApp.resetAgentPositions()">🏠 Reset Positions</button>
            </div>
        `;

        // Calculer et afficher métriques spatiales
        this.calculateSpatialMetrics(agentsData);
    }
};

ICGS3DCore.prototype.generateSectorsDistributionHTML = function(sectorsSummary) {
    let html = '';
    Object.keys(sectorsSummary).forEach(sector => {
        const data = sectorsSummary[sector];
        const color = `#${ICGS3DApp.sectorColors[sector].toString(16).padStart(6, '0')}`;

        html += `
            <div class="metric-card" style="border-left: 3px solid ${color}">
                <h4>${sector}</h4>
                <p>Agents: ${data.count}</p>
                <p>Centre: (${data.center.x.toFixed(1)}, ${data.center.y.toFixed(1)}, ${data.center.z.toFixed(1)})</p>
            </div>
        `;
    });
    return html;
};

ICGS3DCore.prototype.calculateSpatialMetrics = function(agentsData) {
    // Calculer dispersion moyenne
    let totalDispersion = 0;
    let agentCount = 0;

    Object.keys(agentsData.sectors_summary).forEach(sector => {
        const sectorData = agentsData.sectors_summary[sector];
        const center = sectorData.center;

        sectorData.agents.forEach(agent => {
            const distance = Math.sqrt(
                Math.pow(agent.position.x - center.x, 2) +
                Math.pow(agent.position.y - center.y, 2) +
                Math.pow(agent.position.z - center.z, 2)
            );
            totalDispersion += distance;
            agentCount++;
        });
    });

    const avgDispersion = totalDispersion / agentCount;

    // Calculer distance inter-clusters
    const sectors = Object.keys(agentsData.sectors_summary);
    let totalInterDistance = 0;
    let pairCount = 0;

    for (let i = 0; i < sectors.length; i++) {
        for (let j = i + 1; j < sectors.length; j++) {
            const centerA = agentsData.sectors_summary[sectors[i]].center;
            const centerB = agentsData.sectors_summary[sectors[j]].center;

            const distance = Math.sqrt(
                Math.pow(centerA.x - centerB.x, 2) +
                Math.pow(centerA.y - centerB.y, 2) +
                Math.pow(centerA.z - centerB.z, 2)
            );

            totalInterDistance += distance;
            pairCount++;
        }
    }

    const avgInterDistance = totalInterDistance / pairCount;
    const clusteringDensity = (avgInterDistance / avgDispersion).toFixed(2);

    // Mettre à jour interface
    const avgDispersionEl = document.getElementById('avg-dispersion');
    const interDistanceEl = document.getElementById('inter-cluster-distance');
    const densityEl = document.getElementById('clustering-density');

    if (avgDispersionEl) avgDispersionEl.textContent = avgDispersion.toFixed(2);
    if (interDistanceEl) interDistanceEl.textContent = avgInterDistance.toFixed(2);
    if (densityEl) densityEl.textContent = clusteringDensity;
};

ICGS3DCore.prototype.animateClusteringEffects = function() {
    console.log('✨ Animation effets clustering...');

    const animateClusters = () => {
        const clustering = ICGS3DApp.sectorClustering;
        if (!clustering) return;

        const time = Date.now() * 0.001 * clustering.animationSpeed;

        // Animation rotation des centres de clusters
        Object.keys(clustering.clusters).forEach(sector => {
            const cluster = clustering.clusters[sector];
            const centerMesh = ICGS3DApp.scene.getObjectByName(`center_${sector}`);

            if (centerMesh) {
                centerMesh.rotation.y = time * 0.5;

                // Pulsation subtile
                const scale = 1 + 0.1 * Math.sin(time * 2);
                centerMesh.scale.set(scale, scale, scale);
            }
        });

        // Animation flottement des agents
        clustering.agents.forEach(agent => {
            const agentMesh = ICGS3DApp.scene.getObjectByName(`agent_${agent.id}`);
            if (agentMesh && agentMesh.userData.originalPosition) {
                const originalPos = agentMesh.userData.originalPosition;
                const floatOffset = 0.2;

                agentMesh.position.y = originalPos.y + Math.sin(time + agent.id.length) * floatOffset;
            }
        });

        requestAnimationFrame(animateClusters);
    };

    animateClusters();
};

ICGS3DCore.prototype.toggleConnectionsVisibility = function(visible) {
    if (ICGS3DApp.sectorClustering.connectionsGroup) {
        ICGS3DApp.sectorClustering.connectionsGroup.visible = visible;
    }
};

ICGS3DCore.prototype.toggleBoundariesVisibility = function(visible) {
    if (ICGS3DApp.sectorClustering.boundariesGroup) {
        ICGS3DApp.sectorClustering.boundariesGroup.visible = visible;
    }
};

ICGS3DCore.prototype.toggleSectorVisibility = function(sector, visible) {
    const cluster = ICGS3DApp.sectorClustering.clusters[sector];
    if (cluster && cluster.group) {
        cluster.group.visible = visible;
    }
};

ICGS3DCore.prototype.reshuffleClusters = function() {
    console.log('🔄 Réorganisation clusters...');

    const clustering = ICGS3DApp.sectorClustering;
    if (!clustering) return;

    // Nouvelles positions aléatoires pour centres
    Object.keys(clustering.clusters).forEach(sector => {
        const cluster = clustering.clusters[sector];

        // Nouveau centre aléatoire
        const newCenter = {
            x: (Math.random() - 0.5) * 20,
            y: (Math.random() - 0.5) * 20,
            z: (Math.random() - 0.5) * 20
        };

        // Déplacer centre
        const centerMesh = ICGS3DApp.scene.getObjectByName(`center_${sector}`);
        if (centerMesh) {
            centerMesh.position.set(newCenter.x, newCenter.y, newCenter.z);
        }

        // Repositionner agents autour du nouveau centre
        cluster.agents.forEach(agent => {
            const agentMesh = ICGS3DApp.scene.getObjectByName(`agent_${agent.id}`);
            if (agentMesh) {
                const dispersion = 3;
                const newPos = {
                    x: newCenter.x + (Math.random() - 0.5) * dispersion,
                    y: newCenter.y + (Math.random() - 0.5) * dispersion,
                    z: newCenter.z + (Math.random() - 0.5) * dispersion
                };

                // Animation vers nouvelle position
                this.animateAgentToPosition(agentMesh, newPos);
            }
        });

        // Mettre à jour limite cluster
        const boundary = ICGS3DApp.scene.getObjectByName(`boundary_${sector}`);
        if (boundary) {
            boundary.position.set(newCenter.x, newCenter.y, newCenter.z);
        }
    });

    this.showNotification('Clusters réorganisés', 'info');
};

ICGS3DCore.prototype.resetAgentPositions = function() {
    console.log('🏠 Reset positions agents...');

    const clustering = ICGS3DApp.sectorClustering;
    if (!clustering) return;

    clustering.agents.forEach(agent => {
        const agentMesh = ICGS3DApp.scene.getObjectByName(`agent_${agent.id}`);
        if (agentMesh && agentMesh.userData.originalPosition) {
            this.animateAgentToPosition(agentMesh, agentMesh.userData.originalPosition);
        }
    });

    this.showNotification('Positions réinitialisées', 'info');
};

ICGS3DCore.prototype.animateAgentToPosition = function(agentMesh, targetPosition) {
    const startPosition = agentMesh.position.clone();
    const duration = 1000; // 1 seconde
    const startTime = Date.now();

    const animatePosition = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Interpolation smooth
        const easedProgress = 0.5 * (1 - Math.cos(progress * Math.PI));

        agentMesh.position.lerpVectors(startPosition, new THREE.Vector3(targetPosition.x, targetPosition.y, targetPosition.z), easedProgress);

        if (progress < 1) {
            requestAnimationFrame(animatePosition);
        }
    };

    animatePosition();
};

ICGS3DCore.prototype.updateClusteringMethod = function(method) {
    console.log(`🔄 Changement méthode clustering: ${method}`);

    ICGS3DApp.sectorClustering.clusteringMethod = method;

    const methodEl = document.getElementById('clustering-method');
    if (methodEl) methodEl.textContent = method;

    // TODO: Implémenter différentes méthodes de clustering
    this.showNotification(`Méthode clustering: ${method}`, 'info');
};

ICGS3DCore.prototype.loadSimplexViewer = async function() {
    console.log('📈 Chargement Simplex Viewer Animation...');

    // Nettoyer scène pour Simplex
    this.clearScene3D();

    // Créer animation Simplex
    await this.createSimplexAnimation();

    // Mettre à jour interface Simplex
    this.updateSimplexInterface();

    console.log('✅ Simplex Viewer chargé');
};

ICGS3DCore.prototype.createSimplexAnimation = async function() {
    console.log('🎬 Création animation Simplex algorithme...');

    // Récupérer données Simplex depuis ICGS
    const simplexData = await this.getSimplexData();

    // Configuration animation Simplex
    ICGS3DApp.simplexAnimation = {
        currentStep: 0,
        totalSteps: 0,
        isPlaying: false,
        playbackSpeed: 1.0,
        vertices: [],
        constraints: [],
        objectiveFunction: null,
        currentSolution: null,
        path: [],
        feasibleRegion: null
    };

    // Créer région réalisable 3D
    this.createFeasibleRegion(simplexData);

    // Créer visualisation contraintes
    this.createConstraintsVisualization(simplexData);

    // Créer chemin algorithme
    this.createAlgorithmPath(simplexData);

    // Créer contrôles animation
    this.createSimplexControls();

    // Animation personnalisée pour particules Simplex
    this.animateSimplexParticles();
};

ICGS3DCore.prototype.getSimplexData = async function() {
    try {
        // Récupérer analyse Simplex depuis backend
        const response = await fetch('/api/economy/simplex_analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agents_mode: '65_agents',
                optimization_type: 'MAXIMIZE_FEASIBILITY',
                step_by_step: true
            })
        });

        if (response.ok) {
            const data = await response.json();
            console.log('📊 Données Simplex récupérées:', data);
            return data;
        } else {
            // Données simulées pour démo
            return this.generateMockSimplexData();
        }
    } catch (error) {
        console.warn('Utilisation données Simplex simulées:', error);
        return this.generateMockSimplexData();
    }
};

ICGS3DCore.prototype.generateMockSimplexData = function() {
    return {
        problem: {
            objective: { x1: 2, x2: 3, x3: 1, type: 'maximize' },
            constraints: [
                { x1: 1, x2: 1, x3: 0, relation: '<=', value: 4 },
                { x1: 2, x2: 0, x3: 1, relation: '<=', value: 6 },
                { x1: 0, x2: 1, x3: 2, relation: '<=', value: 5 }
            ]
        },
        steps: [
            { vertex: [0, 0, 0], value: 0, entering: 'x2', leaving: null, iteration: 0 },
            { vertex: [0, 4, 0], value: 12, entering: 'x1', leaving: 's1', iteration: 1 },
            { vertex: [2, 2, 0], value: 10, entering: 'x3', leaving: 's2', iteration: 2 },
            { vertex: [1.5, 1.5, 1.5], value: 12.75, entering: null, leaving: null, iteration: 3 }
        ],
        optimal_solution: { x1: 1.5, x2: 1.5, x3: 1.5, value: 12.75 },
        feasible_region: {
            vertices: [
                [0, 0, 0], [4, 0, 0], [0, 4, 0], [0, 0, 2.5],
                [2, 2, 0], [1.5, 1.5, 1.5], [0, 1, 2]
            ]
        }
    };
};

ICGS3DCore.prototype.createFeasibleRegion = function(simplexData) {
    console.log('🎯 Création région réalisable 3D...');

    const vertices = simplexData.feasible_region.vertices;

    // Géométrie région réalisable (convex hull ou approximation)
    let geometry;
    try {
        if (THREE.ConvexGeometry) {
            geometry = new THREE.ConvexGeometry(
                vertices.map(v => new THREE.Vector3(v[0], v[1], v[2]))
            );
        } else {
            // Fallback: utiliser une sphère approximative
            geometry = new THREE.SphereGeometry(4, 16, 16);
            console.warn('ConvexGeometry non disponible, utilisation sphère approximative');
        }
    } catch (error) {
        console.warn('Erreur ConvexGeometry:', error);
        geometry = new THREE.SphereGeometry(4, 16, 16);
    }

    // Matériau semi-transparent
    const material = new THREE.MeshLambertMaterial({
        color: 0x00ffff,
        transparent: true,
        opacity: 0.2,
        side: THREE.DoubleSide
    });

    const feasibleMesh = new THREE.Mesh(geometry, material);
    feasibleMesh.name = 'feasible_region';
    ICGS3DApp.scene.add(feasibleMesh);

    // Contours région
    const wireframe = new THREE.WireframeGeometry(geometry);
    const wireframeMaterial = new THREE.LineBasicMaterial({
        color: 0x00ffff,
        linewidth: 2
    });
    const wireframeMesh = new THREE.LineSegments(wireframe, wireframeMaterial);
    wireframeMesh.name = 'feasible_wireframe';
    ICGS3DApp.scene.add(wireframeMesh);

    // Stocker vertices pour animation
    ICGS3DApp.simplexAnimation.vertices = vertices.map(v =>
        new THREE.Vector3(v[0], v[1], v[2])
    );
};

ICGS3DCore.prototype.createConstraintsVisualization = function(simplexData) {
    console.log('📐 Visualisation contraintes 3D...');

    const constraints = simplexData.problem.constraints;

    constraints.forEach((constraint, index) => {
        // Créer plan pour chaque contrainte
        const plane = this.createConstraintPlane(constraint, index);
        plane.name = `constraint_${index}`;
        ICGS3DApp.scene.add(plane);

        // Étiquette contrainte
        const label = this.createConstraintLabel(constraint, index);
        ICGS3DApp.scene.add(label);
    });
};

ICGS3DCore.prototype.createConstraintPlane = function(constraint, index) {
    // Calcul normal du plan: ax + by + cz = d
    const normal = new THREE.Vector3(constraint.x1, constraint.x2, constraint.x3);
    normal.normalize();

    // Géométrie plan
    const geometry = new THREE.PlaneGeometry(8, 8);

    // Couleurs alternées pour contraintes
    const colors = [0xff4444, 0x44ff44, 0x4444ff, 0xffff44, 0xff44ff];
    const color = colors[index % colors.length];

    const material = new THREE.MeshLambertMaterial({
        color: color,
        transparent: true,
        opacity: 0.3,
        side: THREE.DoubleSide
    });

    const plane = new THREE.Mesh(geometry, material);

    // Positionner et orienter plan
    const d = constraint.value;
    const distance = d / normal.length();
    plane.position.copy(normal.clone().multiplyScalar(distance));
    plane.lookAt(normal.clone().add(plane.position));

    return plane;
};

ICGS3DCore.prototype.createConstraintLabel = function(constraint, index) {
    // Texte contrainte
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 256;
    canvas.height = 64;

    context.fillStyle = '#000000';
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = '#ffffff';
    context.font = '16px Arial';
    context.textAlign = 'center';

    const text = `${constraint.x1}x₁ + ${constraint.x2}x₂ + ${constraint.x3}x₃ ≤ ${constraint.value}`;
    context.fillText(text, canvas.width / 2, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.MeshBasicMaterial({
        map: texture,
        transparent: true
    });

    const geometry = new THREE.PlaneGeometry(2, 0.5);
    const label = new THREE.Mesh(geometry, material);

    // Position étiquette
    const normal = new THREE.Vector3(constraint.x1, constraint.x2, constraint.x3);
    normal.normalize();
    const distance = constraint.value / normal.length();
    label.position.copy(normal.clone().multiplyScalar(distance + 1));

    return label;
};

ICGS3DCore.prototype.createAlgorithmPath = function(simplexData) {
    console.log('🛤️ Création chemin algorithme Simplex...');

    const steps = simplexData.steps;
    ICGS3DApp.simplexAnimation.totalSteps = steps.length;

    // Points du chemin
    const pathPoints = steps.map(step =>
        new THREE.Vector3(step.vertex[0], step.vertex[1], step.vertex[2])
    );

    // Géométrie chemin
    const pathGeometry = new THREE.BufferGeometry().setFromPoints(pathPoints);
    const pathMaterial = new THREE.LineBasicMaterial({
        color: 0xffff00,
        linewidth: 3
    });

    const pathLine = new THREE.Line(pathGeometry, pathMaterial);
    pathLine.name = 'algorithm_path';
    ICGS3DApp.scene.add(pathLine);

    // Marqueurs vertices
    steps.forEach((step, index) => {
        const marker = this.createVertexMarker(step, index);
        marker.name = `vertex_${index}`;
        ICGS3DApp.scene.add(marker);
    });

    // Stocker chemin
    ICGS3DApp.simplexAnimation.path = pathPoints;
};

ICGS3DCore.prototype.createVertexMarker = function(step, index) {
    // Sphère pour vertex
    const geometry = new THREE.SphereGeometry(0.1, 16, 16);
    const material = new THREE.MeshLambertMaterial({
        color: index === 0 ? 0x00ff00 : (step.entering ? 0xffff00 : 0xff0000)
    });

    const sphere = new THREE.Mesh(geometry, material);
    sphere.position.set(step.vertex[0], step.vertex[1], step.vertex[2]);

    // Animation pulsation
    sphere.userData = { originalScale: 1, step: index };

    return sphere;
};

ICGS3DCore.prototype.createSimplexControls = function() {
    console.log('🎮 Création contrôles animation Simplex...');

    // Créer panneau contrôles dat.GUI
    if (window.dat) {
        // Supprimer GUI existant
        if (window.simplexGUI) {
            window.simplexGUI.destroy();
        }

        window.simplexGUI = new dat.GUI({ name: 'Contrôles Simplex' });

        const controls = {
            currentStep: 0,
            isPlaying: false,
            playbackSpeed: 1.0,
            showConstraints: true,
            showPath: true,
            showVertices: true,
            play: () => this.playSimplexAnimation(),
            pause: () => this.pauseSimplexAnimation(),
            reset: () => this.resetSimplexAnimation(),
            nextStep: () => this.nextSimplexStep(),
            prevStep: () => this.prevSimplexStep()
        };

        // Contrôles lecture
        const playbackFolder = window.simplexGUI.addFolder('Lecture');
        playbackFolder.add(controls, 'play').name('▶ Play');
        playbackFolder.add(controls, 'pause').name('⏸ Pause');
        playbackFolder.add(controls, 'reset').name('🔄 Reset');
        playbackFolder.add(controls, 'nextStep').name('⏭ Étape suivante');
        playbackFolder.add(controls, 'prevStep').name('⏮ Étape précédente');

        // Contrôles vitesse
        const speedFolder = window.simplexGUI.addFolder('Vitesse');
        speedFolder.add(controls, 'playbackSpeed', 0.1, 3.0).name('Vitesse').onChange(speed => {
            ICGS3DApp.simplexAnimation.playbackSpeed = speed;
        });

        // Contrôles affichage
        const displayFolder = window.simplexGUI.addFolder('Affichage');
        displayFolder.add(controls, 'showConstraints').name('Contraintes').onChange(show => {
            this.toggleConstraintsVisibility(show);
        });
        displayFolder.add(controls, 'showPath').name('Chemin algorithme').onChange(show => {
            this.togglePathVisibility(show);
        });
        displayFolder.add(controls, 'showVertices').name('Vertices').onChange(show => {
            this.toggleVerticesVisibility(show);
        });

        // Stocker référence contrôles
        ICGS3DApp.simplexControls = controls;

        playbackFolder.open();
        speedFolder.open();
        displayFolder.open();
    }
};

ICGS3DCore.prototype.updateSimplexInterface = function() {
    console.log('🖥️ Mise à jour interface Simplex...');

    // Mettre à jour panneau droite avec infos Simplex
    const pageContent = document.querySelector('.page-content');
    if (pageContent) {
        pageContent.innerHTML = `
            <div class="page-header">
                <h2 class="page-title">Simplex Viewer</h2>
                <p class="page-subtitle">Animation algorithme étape par étape</p>
            </div>

            <div class="controls-section">
                <h4>État Algorithme</h4>
                <div id="simplex-status">
                    <p><strong>Étape:</strong> <span id="current-step">0</span> / <span id="total-steps">0</span></p>
                    <p><strong>Solution courante:</strong> <span id="current-solution">Initialisation...</span></p>
                    <p><strong>Valeur objective:</strong> <span id="objective-value">0</span></p>
                </div>
            </div>

            <div class="controls-section">
                <h4>Problème d'Optimisation</h4>
                <div id="problem-definition">
                    <p><strong>Maximiser:</strong> 2x₁ + 3x₂ + x₃</p>
                    <p><strong>Contraintes:</strong></p>
                    <ul>
                        <li>x₁ + x₂ ≤ 4</li>
                        <li>2x₁ + x₃ ≤ 6</li>
                        <li>x₂ + 2x₃ ≤ 5</li>
                        <li>x₁, x₂, x₃ ≥ 0</li>
                    </ul>
                </div>
            </div>

            <div class="controls-section">
                <h4>Historique Itérations</h4>
                <div id="iteration-history">
                    <!-- Dynamiquement rempli par JS -->
                </div>
            </div>

            <div class="controls-section">
                <h4>Contrôles Rapides</h4>
                <button class="btn" onclick="icgs3dApp.playSimplexAnimation()">▶ Play</button>
                <button class="btn btn-secondary" onclick="icgs3dApp.pauseSimplexAnimation()">⏸ Pause</button>
                <button class="btn btn-danger" onclick="icgs3dApp.resetSimplexAnimation()">🔄 Reset</button>
            </div>
        `;

        // Mettre à jour statistiques initiales
        this.updateSimplexStats();
    }
};

ICGS3DCore.prototype.updateSimplexStats = function() {
    const animation = ICGS3DApp.simplexAnimation;
    if (!animation) return;

    // Mettre à jour compteurs
    const currentStepEl = document.getElementById('current-step');
    const totalStepsEl = document.getElementById('total-steps');
    if (currentStepEl) currentStepEl.textContent = animation.currentStep;
    if (totalStepsEl) totalStepsEl.textContent = animation.totalSteps;

    // Mettre à jour solution courante
    const currentSolutionEl = document.getElementById('current-solution');
    if (currentSolutionEl && animation.currentSolution) {
        const solution = animation.currentSolution;
        currentSolutionEl.textContent = `(${solution.vertex.join(', ')})`;
    }

    // Mettre à jour valeur objective
    const objectiveValueEl = document.getElementById('objective-value');
    if (objectiveValueEl && animation.currentSolution) {
        objectiveValueEl.textContent = animation.currentSolution.value.toFixed(2);
    }
};

ICGS3DCore.prototype.playSimplexAnimation = function() {
    console.log('▶ Démarrage animation Simplex...');

    const animation = ICGS3DApp.simplexAnimation;
    if (!animation) return;

    animation.isPlaying = true;

    // Animation automatique avec intervalles
    animation.playInterval = setInterval(() => {
        if (animation.isPlaying && animation.currentStep < animation.totalSteps - 1) {
            this.nextSimplexStep();
        } else {
            this.pauseSimplexAnimation();
        }
    }, 2000 / animation.playbackSpeed); // Vitesse adaptable
};

ICGS3DCore.prototype.pauseSimplexAnimation = function() {
    console.log('⏸ Pause animation Simplex...');

    const animation = ICGS3DApp.simplexAnimation;
    if (!animation) return;

    animation.isPlaying = false;
    if (animation.playInterval) {
        clearInterval(animation.playInterval);
    }
};

ICGS3DCore.prototype.resetSimplexAnimation = function() {
    console.log('🔄 Reset animation Simplex...');

    this.pauseSimplexAnimation();

    const animation = ICGS3DApp.simplexAnimation;
    if (!animation) return;

    animation.currentStep = 0;
    this.gotoSimplexStep(0);
};

ICGS3DCore.prototype.nextSimplexStep = function() {
    const animation = ICGS3DApp.simplexAnimation;
    if (!animation || animation.currentStep >= animation.totalSteps - 1) return;

    animation.currentStep++;
    this.gotoSimplexStep(animation.currentStep);
};

ICGS3DCore.prototype.prevSimplexStep = function() {
    const animation = ICGS3DApp.simplexAnimation;
    if (!animation || animation.currentStep <= 0) return;

    animation.currentStep--;
    this.gotoSimplexStep(animation.currentStep);
};

ICGS3DCore.prototype.gotoSimplexStep = function(stepIndex) {
    console.log(`🎯 Navigation vers étape ${stepIndex}...`);

    const animation = ICGS3DApp.simplexAnimation;
    if (!animation || !animation.path) return;

    // Mettre à jour vertices visuels
    for (let i = 0; i < animation.totalSteps; i++) {
        const vertex = ICGS3DApp.scene.getObjectByName(`vertex_${i}`);
        if (vertex) {
            if (i <= stepIndex) {
                // Vertex visité - vert
                vertex.material.color.setHex(i === stepIndex ? 0xffff00 : 0x00ff00);
                vertex.scale.set(i === stepIndex ? 1.5 : 1, i === stepIndex ? 1.5 : 1, i === stepIndex ? 1.5 : 1);
            } else {
                // Vertex non visité - rouge
                vertex.material.color.setHex(0xff0000);
                vertex.scale.set(1, 1, 1);
            }
        }
    }

    // Animation caméra vers vertex courant
    const currentVertex = animation.path[stepIndex];
    if (currentVertex) {
        const targetPosition = currentVertex.clone().add(new THREE.Vector3(5, 5, 5));
        this.animateCameraTo(targetPosition, currentVertex);
    }

    // Mettre à jour solution courante
    // TODO: Récupérer données étape depuis simplexData
    animation.currentSolution = {
        vertex: animation.path[stepIndex].toArray(),
        value: stepIndex * 2.5 // Valeur simulée
    };

    // Mettre à jour interface
    this.updateSimplexStats();

    console.log(`✅ Animation à l'étape ${stepIndex}`);
};

ICGS3DCore.prototype.animateCameraTo = function(position, lookAt) {
    const camera = ICGS3DApp.camera;
    const controls = ICGS3DApp.controls;

    if (!camera || !controls) return;

    // Animation smooth de la caméra
    const startPosition = camera.position.clone();
    const startTarget = controls.target.clone();

    let progress = 0;
    const duration = 1000; // 1 seconde
    const startTime = Date.now();

    const animateCamera = () => {
        const elapsed = Date.now() - startTime;
        progress = Math.min(elapsed / duration, 1);

        // Interpolation smooth
        const easedProgress = 0.5 * (1 - Math.cos(progress * Math.PI));

        camera.position.lerpVectors(startPosition, position, easedProgress);
        if (controls) {
            controls.target.lerpVectors(startTarget, lookAt, easedProgress);
            controls.update();
        }

        if (progress < 1) {
            requestAnimationFrame(animateCamera);
        }
    };

    animateCamera();
};

ICGS3DCore.prototype.animateSimplexParticles = function() {
    console.log('✨ Animation particules Simplex...');

    // Animation spéciale pour mode Simplex
    const animateParticles = () => {
        const animation = ICGS3DApp.simplexAnimation;
        if (!animation) return;

        // Animation des marqueurs vertices avec pulsation
        for (let i = 0; i < animation.totalSteps; i++) {
            const vertex = ICGS3DApp.scene.getObjectByName(`vertex_${i}`);
            if (vertex && i === animation.currentStep) {
                const time = Date.now() * 0.005;
                const scale = 1 + 0.3 * Math.sin(time);
                vertex.scale.set(scale, scale, scale);
            }
        }

        requestAnimationFrame(animateParticles);
    };

    animateParticles();
};

ICGS3DCore.prototype.toggleConstraintsVisibility = function(visible) {
    const constraints = ICGS3DApp.scene.children.filter(obj =>
        obj.name.startsWith('constraint_')
    );
    constraints.forEach(constraint => {
        constraint.visible = visible;
    });
};

ICGS3DCore.prototype.togglePathVisibility = function(visible) {
    const path = ICGS3DApp.scene.getObjectByName('algorithm_path');
    if (path) path.visible = visible;
};

ICGS3DCore.prototype.toggleVerticesVisibility = function(visible) {
    const vertices = ICGS3DApp.scene.children.filter(obj =>
        obj.name.startsWith('vertex_')
    );
    vertices.forEach(vertex => {
        vertex.visible = visible;
    });
};

ICGS3DCore.prototype.loadDataExport = async function() {
    console.log('📁 Chargement Data Export multi-format...');

    // Nettoyer scène pour export
    this.clearScene3D();

    // Charger données exportables
    const exportData = await this.loadExportableData();

    // Créer visualisation données export
    await this.createDataExportVisualization(exportData);

    // Mettre à jour interface export
    this.updateDataExportInterface(exportData);

    console.log('✅ Data Export chargé');
};

ICGS3DCore.prototype.loadExportableData = async function() {
    try {
        // Récupérer toutes les données économiques pour export
        const response = await fetch('/api/economy/export_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agents_mode: '65_agents',
                include_performance: true,
                include_3d_positions: true,
                include_transactions: true,
                include_simplex_analysis: true
            })
        });

        if (response.ok) {
            const data = await response.json();
            console.log('📊 Données export récupérées:', data);
            return data;
        } else {
            return this.generateMockExportData();
        }
    } catch (error) {
        console.warn('Utilisation données export simulées:', error);
        return this.generateMockExportData();
    }
};

ICGS3DCore.prototype.generateMockExportData = function() {
    // Génération données simulées complètes pour export
    const sectors = Object.keys(ICGS3DApp.sectorColors);
    const agentCounts = { 'AGRICULTURE': 10, 'INDUSTRY': 15, 'SERVICES': 20, 'FINANCE': 8, 'ENERGY': 12 };

    const exportData = {
        timestamp: new Date().toISOString(),
        simulation_config: {
            agents_mode: '65_agents',
            total_agents: 65,
            sectors: sectors.length
        },
        agents: [],
        transactions: [],
        performance_metrics: {
            cache_hit_rate: 0.74,
            avg_validation_time: 12.5,
            memory_usage: 256,
            particle_count: 2000
        },
        sector_analysis: {},
        simplex_results: {
            optimal_value: 12.75,
            solution: { x1: 1.5, x2: 1.5, x3: 1.5 },
            iterations: 4
        },
        spatial_metrics: {}
    };

    // Générer agents détaillés
    let agentId = 0;
    sectors.forEach(sector => {
        const count = agentCounts[sector] || 5;
        const center = this.getSectorClusterCenter(sector);
        const sectorAgents = [];

        for (let i = 0; i < count; i++) {
            const agent = {
                id: `${sector}_${i.toString().padStart(2, '0')}`,
                sector: sector,
                balance: 1000 + Math.random() * 500,
                position_3d: {
                    x: center.x + (Math.random() - 0.5) * 6,
                    y: center.y + (Math.random() - 0.5) * 6,
                    z: center.z + (Math.random() - 0.5) * 6
                },
                activity_level: Math.random(),
                connections_count: Math.floor(Math.random() * 5) + 2,
                last_transaction: new Date(Date.now() - Math.random() * 86400000).toISOString(),
                performance_score: Math.random() * 100
            };
            sectorAgents.push(agent);
            exportData.agents.push(agent);
            agentId++;
        }

        exportData.sector_analysis[sector] = {
            count: count,
            total_balance: sectorAgents.reduce((sum, a) => sum + a.balance, 0),
            avg_activity: sectorAgents.reduce((sum, a) => sum + a.activity_level, 0) / count,
            center_position: center
        };
    });

    // Générer transactions simulées
    for (let i = 0; i < 50; i++) {
        const sourceAgent = exportData.agents[Math.floor(Math.random() * exportData.agents.length)];
        const targetAgent = exportData.agents[Math.floor(Math.random() * exportData.agents.length)];

        if (sourceAgent.id !== targetAgent.id) {
            exportData.transactions.push({
                id: `TX_${i.toString().padStart(3, '0')}`,
                source: sourceAgent.id,
                target: targetAgent.id,
                amount: Math.floor(Math.random() * 500) + 50,
                timestamp: new Date(Date.now() - Math.random() * 3600000).toISOString(),
                status: Math.random() > 0.2 ? 'FEASIBLE' : 'INFEASIBLE',
                validation_time: Math.random() * 20 + 1
            });
        }
    }

    return exportData;
};

ICGS3DCore.prototype.createDataExportVisualization = async function(exportData) {
    console.log('📊 Création visualisation export données...');

    // Configuration export
    ICGS3DApp.dataExport = {
        data: exportData,
        selectedFormats: ['JSON', 'CSV'],
        previewMode: 'agents',
        exportFilters: {
            dateRange: 'all',
            sectors: 'all',
            includePerformance: true,
            include3DPositions: true
        }
    };

    // Créer preview 3D des données
    this.createDataPreview3D(exportData);

    // Créer graphiques statistiques
    this.createExportStatistics(exportData);

    // Créer contrôles export
    this.createExportControls();
};

ICGS3DCore.prototype.createDataPreview3D = function(exportData) {
    console.log('👁️ Création preview 3D données...');

    // Visualisation agents comme nuage de points
    const agentsGroup = new THREE.Group();
    agentsGroup.name = 'export_agents_preview';

    exportData.agents.forEach(agent => {
        const geometry = new THREE.SphereGeometry(0.05, 8, 8);
        const color = ICGS3DApp.sectorColors[agent.sector];
        const material = new THREE.MeshBasicMaterial({
            color: color,
            transparent: true,
            opacity: 0.8
        });

        const sphere = new THREE.Mesh(geometry, material);
        sphere.position.set(
            agent.position_3d.x * 0.5, // Échelle réduite pour preview
            agent.position_3d.y * 0.5,
            agent.position_3d.z * 0.5
        );

        sphere.userData = { agent: agent };
        agentsGroup.add(sphere);
    });

    ICGS3DApp.scene.add(agentsGroup);

    // Visualisation flux transactions
    this.createTransactionsFlow3D(exportData);

    // Stats floating texts
    this.createFloatingStatistics(exportData);
};

ICGS3DCore.prototype.createTransactionsFlow3D = function(exportData) {
    const flowGroup = new THREE.Group();
    flowGroup.name = 'export_transactions_flow';

    // Sélectionner 20 transactions récentes pour visualisation
    const recentTransactions = exportData.transactions
        .filter(tx => tx.status === 'FEASIBLE')
        .slice(0, 20);

    recentTransactions.forEach(transaction => {
        const sourceAgent = exportData.agents.find(a => a.id === transaction.source);
        const targetAgent = exportData.agents.find(a => a.id === transaction.target);

        if (sourceAgent && targetAgent) {
            const points = [
                new THREE.Vector3(
                    sourceAgent.position_3d.x * 0.5,
                    sourceAgent.position_3d.y * 0.5,
                    sourceAgent.position_3d.z * 0.5
                ),
                new THREE.Vector3(
                    targetAgent.position_3d.x * 0.5,
                    targetAgent.position_3d.y * 0.5,
                    targetAgent.position_3d.z * 0.5
                )
            ];

            const geometry = new THREE.BufferGeometry().setFromPoints(points);
            const material = new THREE.LineBasicMaterial({
                color: 0x00ff88,
                transparent: true,
                opacity: 0.6
            });

            const line = new THREE.Line(geometry, material);
            line.userData = { transaction: transaction };
            flowGroup.add(line);
        }
    });

    ICGS3DApp.scene.add(flowGroup);
    ICGS3DApp.dataExport.flowGroup = flowGroup;
};

ICGS3DCore.prototype.createFloatingStatistics = function(exportData) {
    const stats = [
        { text: `${exportData.agents.length} Agents`, position: [-8, 6, 0] },
        { text: `${exportData.transactions.length} Transactions`, position: [8, 6, 0] },
        { text: `${Object.keys(exportData.sector_analysis).length} Secteurs`, position: [0, 8, -6] },
        { text: `Cache: ${(exportData.performance_metrics.cache_hit_rate * 100).toFixed(1)}%`, position: [0, -6, 6] }
    ];

    stats.forEach(stat => {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 200;
        canvas.height = 50;

        context.fillStyle = '#000000';
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.fillStyle = '#00ffff';
        context.font = 'bold 14px Arial';
        context.textAlign = 'center';
        context.fillText(stat.text, canvas.width / 2, canvas.height / 2 + 5);

        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.MeshBasicMaterial({
            map: texture,
            transparent: true,
            alphaTest: 0.5
        });

        const geometry = new THREE.PlaneGeometry(2, 0.5);
        const label = new THREE.Mesh(geometry, material);
        label.position.set(stat.position[0], stat.position[1], stat.position[2]);
        label.name = `stat_${stat.text.replace(/\s/g, '_')}`;

        ICGS3DApp.scene.add(label);
    });
};

ICGS3DCore.prototype.createExportStatistics = function(exportData) {
    // Calculer statistiques avancées pour graphiques
    const sectorDistribution = {};
    const balanceDistribution = {};
    const activityDistribution = {};

    exportData.agents.forEach(agent => {
        // Distribution secteurs
        sectorDistribution[agent.sector] = (sectorDistribution[agent.sector] || 0) + 1;

        // Distribution balances
        const balanceRange = Math.floor(agent.balance / 100) * 100;
        balanceDistribution[balanceRange] = (balanceDistribution[balanceRange] || 0) + 1;

        // Distribution activité
        const activityRange = Math.floor(agent.activity_level * 10) / 10;
        activityDistribution[activityRange] = (activityDistribution[activityRange] || 0) + 1;
    });

    ICGS3DApp.dataExport.statistics = {
        sectorDistribution,
        balanceDistribution,
        activityDistribution,
        transactionSuccess: exportData.transactions.filter(tx => tx.status === 'FEASIBLE').length / exportData.transactions.length
    };
};

ICGS3DCore.prototype.createExportControls = function() {
    console.log('🎮 Création contrôles export...');

    // Créer dat.GUI pour export
    if (window.dat) {
        // Supprimer GUI existant
        if (window.exportGUI) {
            window.exportGUI.destroy();
        }

        window.exportGUI = new dat.GUI({ name: 'Contrôles Export' });

        const controls = {
            previewMode: 'agents',
            exportFormat: 'JSON',
            includePerformance: true,
            include3DPositions: true,
            includeTransactions: true,
            dateRange: 'all',
            exportJSON: () => this.exportToJSON(),
            exportCSV: () => this.exportToCSV(),
            exportPNG: () => this.exportToPNG(),
            downloadAll: () => this.downloadAllFormats()
        };

        // Contrôles preview
        const previewFolder = window.exportGUI.addFolder('Preview');
        previewFolder.add(controls, 'previewMode', ['agents', 'transactions', 'sectors', 'performance']).name('Mode Preview').onChange(mode => {
            this.updatePreviewMode(mode);
        });

        // Contrôles filtres
        const filtersFolder = window.exportGUI.addFolder('Filtres');
        filtersFolder.add(controls, 'includePerformance').name('Métriques Performance').onChange(include => {
            ICGS3DApp.dataExport.exportFilters.includePerformance = include;
        });
        filtersFolder.add(controls, 'include3DPositions').name('Positions 3D').onChange(include => {
            ICGS3DApp.dataExport.exportFilters.include3DPositions = include;
        });
        filtersFolder.add(controls, 'includeTransactions').name('Transactions').onChange(include => {
            ICGS3DApp.dataExport.exportFilters.includeTransactions = include;
        });
        filtersFolder.add(controls, 'dateRange', ['all', 'last_hour', 'last_day', 'last_week']).name('Période').onChange(range => {
            ICGS3DApp.dataExport.exportFilters.dateRange = range;
        });

        // Contrôles export
        const exportFolder = window.exportGUI.addFolder('Export');
        exportFolder.add(controls, 'exportJSON').name('📄 Export JSON');
        exportFolder.add(controls, 'exportCSV').name('📊 Export CSV');
        exportFolder.add(controls, 'exportPNG').name('🖼️ Export PNG (3D)');
        exportFolder.add(controls, 'downloadAll').name('📦 Télécharger Tout');

        previewFolder.open();
        filtersFolder.open();
        exportFolder.open();

        // Stocker référence
        ICGS3DApp.exportControls = controls;
    }
};

ICGS3DCore.prototype.updateDataExportInterface = function(exportData) {
    console.log('🖥️ Mise à jour interface Data Export...');

    const pageContent = document.querySelector('.page-content');
    if (pageContent) {
        const totalSize = this.calculateDataSize(exportData);
        const lastUpdate = new Date(exportData.timestamp).toLocaleString();

        pageContent.innerHTML = `
            <div class="page-header">
                <h2 class="page-title">Data Export</h2>
                <p class="page-subtitle">Export multi-format pour analyses externes</p>
            </div>

            <div class="controls-section">
                <h4>Informations Export</h4>
                <div id="export-info">
                    <p><strong>Dernière mise à jour:</strong> ${lastUpdate}</p>
                    <p><strong>Taille données:</strong> ${totalSize} KB</p>
                    <p><strong>Formats disponibles:</strong> JSON, CSV, PNG</p>
                </div>
            </div>

            <div class="controls-section">
                <h4>Contenu Disponible</h4>
                <div id="export-content">
                    ${this.generateExportContentHTML(exportData)}
                </div>
            </div>

            <div class="controls-section">
                <h4>Statistiques Preview</h4>
                <div id="export-statistics">
                    ${this.generateExportStatsHTML(exportData)}
                </div>
            </div>

            <div class="controls-section">
                <h4>Actions Export</h4>
                <button class="btn" onclick="icgs3dApp.exportToJSON()">📄 JSON</button>
                <button class="btn" onclick="icgs3dApp.exportToCSV()">📊 CSV</button>
                <button class="btn" onclick="icgs3dApp.exportToPNG()">🖼️ PNG 3D</button>
                <button class="btn btn-secondary" onclick="icgs3dApp.downloadAllFormats()">📦 Tout</button>
            </div>
        `;
    }
};

ICGS3DCore.prototype.generateExportContentHTML = function(exportData) {
    return `
        <div class="metric-card">
            <h4>Agents Économiques</h4>
            <p>${exportData.agents.length} agents avec positions 3D</p>
            <p>Secteurs: ${Object.keys(exportData.sector_analysis).join(', ')}</p>
        </div>
        <div class="metric-card">
            <h4>Transactions</h4>
            <p>${exportData.transactions.length} transactions</p>
            <p>Taux succès: ${(ICGS3DApp.dataExport.statistics.transactionSuccess * 100).toFixed(1)}%</p>
        </div>
        <div class="metric-card">
            <h4>Métriques Performance</h4>
            <p>Cache hit rate: ${(exportData.performance_metrics.cache_hit_rate * 100).toFixed(1)}%</p>
            <p>Temps validation moyen: ${exportData.performance_metrics.avg_validation_time}ms</p>
        </div>
        <div class="metric-card">
            <h4>Analyse Simplex</h4>
            <p>Valeur optimale: ${exportData.simplex_results.optimal_value}</p>
            <p>Itérations: ${exportData.simplex_results.iterations}</p>
        </div>
    `;
};

ICGS3DCore.prototype.generateExportStatsHTML = function(exportData) {
    const stats = ICGS3DApp.dataExport.statistics;
    let html = '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">';

    // Distribution secteurs
    html += '<div><h5>Distribution Secteurs</h5>';
    Object.keys(stats.sectorDistribution).forEach(sector => {
        const count = stats.sectorDistribution[sector];
        const percentage = ((count / exportData.agents.length) * 100).toFixed(1);
        html += `<p>${sector}: ${count} (${percentage}%)</p>`;
    });
    html += '</div>';

    // Distribution balances
    html += '<div><h5>Distribution Balances</h5>';
    Object.keys(stats.balanceDistribution).slice(0, 5).forEach(range => {
        const count = stats.balanceDistribution[range];
        html += `<p>${range}+: ${count} agents</p>`;
    });
    html += '</div>';

    html += '</div>';
    return html;
};

ICGS3DCore.prototype.calculateDataSize = function(exportData) {
    const jsonString = JSON.stringify(exportData);
    return Math.round(jsonString.length / 1024);
};

ICGS3DCore.prototype.updatePreviewMode = function(mode) {
    console.log(`🔄 Changement mode preview: ${mode}`);
    ICGS3DApp.dataExport.previewMode = mode;

    // Mettre à jour visibilité éléments 3D selon mode
    const agentsGroup = ICGS3DApp.scene.getObjectByName('export_agents_preview');
    const flowGroup = ICGS3DApp.dataExport.flowGroup;

    if (agentsGroup) agentsGroup.visible = mode === 'agents' || mode === 'sectors';
    if (flowGroup) flowGroup.visible = mode === 'transactions';

    this.showNotification(`Mode preview: ${mode}`, 'info');
};

ICGS3DCore.prototype.exportToJSON = function() {
    console.log('📄 Export JSON...');

    const exportData = this.prepareExportData();
    const jsonString = JSON.stringify(exportData, null, 2);

    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `icgs_export_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
    this.showNotification('Export JSON téléchargé', 'success');
};

ICGS3DCore.prototype.exportToCSV = function() {
    console.log('📊 Export CSV...');

    const exportData = this.prepareExportData();

    // CSV des agents
    let csvContent = 'ID,Sector,Balance,Activity_Level,Position_X,Position_Y,Position_Z,Connections_Count,Performance_Score\n';

    exportData.agents.forEach(agent => {
        csvContent += [
            agent.id,
            agent.sector,
            agent.balance.toFixed(2),
            agent.activity_level.toFixed(3),
            agent.position_3d.x.toFixed(3),
            agent.position_3d.y.toFixed(3),
            agent.position_3d.z.toFixed(3),
            agent.connections_count,
            agent.performance_score.toFixed(2)
        ].join(',') + '\n';
    });

    // CSV des transactions
    csvContent += '\n\nTransactions\n';
    csvContent += 'ID,Source,Target,Amount,Status,Timestamp,Validation_Time\n';

    exportData.transactions.forEach(tx => {
        csvContent += [
            tx.id,
            tx.source,
            tx.target,
            tx.amount,
            tx.status,
            tx.timestamp,
            tx.validation_time.toFixed(2)
        ].join(',') + '\n';
    });

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `icgs_export_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
    this.showNotification('Export CSV téléchargé', 'success');
};

ICGS3DCore.prototype.exportToPNG = function() {
    console.log('🖼️ Export PNG 3D...');

    // Capturer rendu Three.js courant
    const renderer = ICGS3DApp.renderer;
    if (!renderer) {
        this.showNotification('Erreur: Renderer non disponible', 'error');
        return;
    }

    // Forcer un rendu de haute qualité
    const originalPixelRatio = renderer.getPixelRatio();
    renderer.setPixelRatio(2); // Haute résolution

    // Render scene
    renderer.render(ICGS3DApp.scene, ICGS3DApp.camera);

    // Capturer image
    const canvas = renderer.domElement;
    const link = document.createElement('a');
    link.download = `icgs_3d_export_${new Date().toISOString().split('T')[0]}.png`;
    link.href = canvas.toDataURL('image/png');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Restaurer qualité originale
    renderer.setPixelRatio(originalPixelRatio);

    this.showNotification('Export PNG 3D téléchargé', 'success');
};

ICGS3DCore.prototype.downloadAllFormats = function() {
    console.log('📦 Téléchargement tous formats...');

    // Télécharger dans l'ordre avec délais
    this.exportToJSON();

    setTimeout(() => {
        this.exportToCSV();
    }, 500);

    setTimeout(() => {
        this.exportToPNG();
    }, 1000);

    this.showNotification('Téléchargement tous formats lancé', 'info');
};

ICGS3DCore.prototype.prepareExportData = function() {
    const originalData = ICGS3DApp.dataExport.data;
    const filters = ICGS3DApp.dataExport.exportFilters;

    // Cloner données et appliquer filtres
    const exportData = JSON.parse(JSON.stringify(originalData));

    // Filtrer selon préférences
    if (!filters.includePerformance) {
        delete exportData.performance_metrics;
    }

    if (!filters.include3DPositions) {
        exportData.agents.forEach(agent => {
            delete agent.position_3d;
        });
    }

    if (!filters.includeTransactions) {
        exportData.transactions = [];
    }

    // Filtrer par date si nécessaire
    if (filters.dateRange !== 'all') {
        const now = Date.now();
        let timeLimit;

        switch (filters.dateRange) {
            case 'last_hour':
                timeLimit = now - 3600000;
                break;
            case 'last_day':
                timeLimit = now - 86400000;
                break;
            case 'last_week':
                timeLimit = now - 604800000;
                break;
        }

        if (timeLimit) {
            exportData.transactions = exportData.transactions.filter(tx =>
                new Date(tx.timestamp).getTime() > timeLimit
            );
        }
    }

    return exportData;
};

// ======================================
// SIMPLEX ANIMATION CONTROLLER
// ======================================

class SimplexAnimationController {
    constructor(icgs3dCore) {
        this.icgs3dCore = icgs3dCore;
        this.mode = 'single';  // 'single' ou 'simulation'
        this.currentAnimation = null;
        this.animationState = 'stopped';  // 'stopped', 'playing', 'paused'
        this.currentStep = 0;
        this.totalSteps = 0;
        this.animationSpeed = 1.0;
        this.currentTransactionData = null;
        this.currentSimulationData = null;

        // Cache pour les transactions
        this.transactionsCache = new Map();
        this.isLoading = false;

        this.initializeEventListeners();
        this.loadAvailableTransactions();
    }

    initializeEventListeners() {
        console.log('🎯 Initialisation SimplexAnimationController event listeners');

        // Mode tabs - Updated to match new HTML structure
        document.getElementById('mode-single-transaction')?.addEventListener('click', () => {
            this.switchMode('single');
        });
        document.getElementById('mode-simulation-complete')?.addEventListener('click', () => {
            this.switchMode('simulation');
        });

        // Animation controls - Updated to match new HTML structure
        document.getElementById('play-animation')?.addEventListener('click', () => {
            if (this.mode === 'single') {
                this.startTransactionAnimation();
            } else {
                this.startCompleteSimulation();
            }
        });

        document.getElementById('pause-animation')?.addEventListener('click', () => {
            this.pauseAnimation();
        });

        document.getElementById('reset-animation')?.addEventListener('click', () => {
            this.resetAnimation();
        });

        // Speed control - Updated to match new HTML structure
        document.getElementById('animation-speed')?.addEventListener('input', (e) => {
            this.animationSpeed = parseFloat(e.target.value);
            document.getElementById('speed-value').textContent = `${this.animationSpeed}x`;
        });

        // Transaction list delegation - Handle clicks on transaction items
        document.getElementById('transaction-list')?.addEventListener('click', (e) => {
            const transactionItem = e.target.closest('.transaction-item');
            if (transactionItem) {
                const transactionId = transactionItem.dataset.transactionId;
                this.selectTransaction(transactionId);
            }
        });
    }

    switchMode(mode) {
        console.log(`🔄 Basculement mode Simplex: ${mode}`);
        this.mode = mode;

        // Update tab states - Updated to match new HTML structure
        document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
        if (mode === 'single') {
            document.getElementById('mode-single-transaction')?.classList.add('active');
        } else if (mode === 'simulation') {
            document.getElementById('mode-simulation-complete')?.classList.add('active');
        }

        // Show/hide mode content - Updated to match new HTML structure
        const transactionPanel = document.getElementById('transaction-selection-panel');
        const simulationPanel = document.getElementById('simulation-control-panel');
        const playButton = document.getElementById('play-animation');

        if (mode === 'single') {
            if (transactionPanel) transactionPanel.style.display = 'block';
            if (simulationPanel) simulationPanel.style.display = 'none';
            if (playButton) playButton.textContent = '▶ Lancer Animation Transaction';
        } else {
            if (transactionPanel) transactionPanel.style.display = 'none';
            if (simulationPanel) simulationPanel.style.display = 'block';
            if (playButton) playButton.textContent = '▶ Lancer Simulation Complète';
        }

        // Reset animation state
        this.resetAnimation();

        // Load mode-specific data
        if (mode === 'simulation') {
            this.loadSimulationInfo();
        } else {
            this.loadAvailableTransactions();
        }
    }

    async loadAvailableTransactions() {
        console.log('📋 Chargement transactions disponibles');
        this.isLoading = true;

        const transactionList = document.getElementById('transaction-list');
        if (transactionList) {
            transactionList.innerHTML = `
                <div class="loading-transactions">
                    <div class="spinner"></div>
                    <p>Chargement transactions...</p>
                </div>
            `;
        }

        try {
            const response = await fetch('/api/simplex_3d/transactions');
            const data = await response.json();

            if (data.success && transactionList) {
                transactionList.innerHTML = '';

                data.transactions.forEach(tx => {
                    const transactionItem = document.createElement('div');
                    transactionItem.className = 'transaction-item';
                    transactionItem.dataset.transactionId = tx.id;

                    transactionItem.innerHTML = `
                        <div class="transaction-header">
                            <strong>${tx.id}</strong>
                            <span class="step-count">${tx.step_count} étapes</span>
                        </div>
                        <div class="transaction-details">
                            <span class="transaction-flow">${tx.source} → ${tx.target}</span>
                            <span class="transaction-amount">${tx.amount || 'N/A'}</span>
                        </div>
                        <div class="transaction-complexity complexity-${tx.complexity.toLowerCase()}">
                            ${tx.complexity}
                        </div>
                    `;

                    transactionList.appendChild(transactionItem);
                });

                console.log(`✅ ${data.transactions.length} transactions chargées`);
            } else {
                console.error('❌ Erreur chargement transactions:', data.error || 'Données invalides');
                if (transactionList) {
                    transactionList.innerHTML = `
                        <div class="error-message">
                            <p>❌ Erreur chargement transactions</p>
                            <button onclick="window.icgs3dApp.simplexController.loadAvailableTransactions()">
                                Réessayer
                            </button>
                        </div>
                    `;
                }
            }
        } catch (error) {
            console.error('❌ Erreur réseau chargement transactions:', error);
            if (transactionList) {
                transactionList.innerHTML = `
                    <div class="error-message">
                        <p>❌ Erreur réseau</p>
                        <button onclick="window.icgs3dApp.simplexController.loadAvailableTransactions()">
                            Réessayer
                        </button>
                    </div>
                `;
            }
        } finally {
            this.isLoading = false;
        }
    }

    async loadTransactionData(transactionId) {
        console.log(`🔍 Chargement données transaction: ${transactionId}`);

        // Vérifier cache
        if (this.transactionsCache.has(transactionId)) {
            this.displayTransactionInfo(this.transactionsCache.get(transactionId));
            return;
        }

        try {
            const response = await fetch(`/api/simplex_3d/transaction/${transactionId}`);
            const data = await response.json();

            if (data.success) {
                this.transactionsCache.set(transactionId, data);
                this.currentTransactionData = data;
                this.displayTransactionInfo(data);
                console.log(`✅ Données transaction ${transactionId} chargées: ${data.step_count} étapes`);
            } else {
                console.error('❌ Erreur chargement données transaction:', data.error);
            }
        } catch (error) {
            console.error('❌ Erreur réseau chargement données:', error);
        }
    }

    displayTransactionInfo(data) {
        console.log('📊 Affichage informations transaction');

        // Update info values
        document.getElementById('step-count').textContent = data.step_count;
        document.getElementById('duration').textContent = `${data.estimated_duration_ms}ms`;
        document.getElementById('complexity').textContent = data.complexity_level;
        document.getElementById('source-account').textContent = data.transaction_info.source_account;
        document.getElementById('target-account').textContent = data.transaction_info.target_account;
        document.getElementById('amount').textContent = data.transaction_info.amount.toFixed(2);

        // Show transaction info panel
        document.getElementById('transaction-info').style.display = 'block';

        // Enable animation button
        const animateBtn = document.getElementById('animate-transaction-btn');
        if (animateBtn) {
            animateBtn.disabled = false;
            animateBtn.textContent = `🎬 Animer Transaction (${data.step_count} étapes)`;
        }
    }

    async loadSimulationInfo() {
        console.log('🚀 Chargement informations simulation complète');

        try {
            const response = await fetch('/api/simplex_3d/simulation/status');
            const data = await response.json();

            if (data.success) {
                document.getElementById('total-transactions').textContent = data.total_transactions;
                document.getElementById('total-steps').textContent = '...';  // Sera calculé au lancement
                document.getElementById('total-duration').textContent = '...';

                // Enable start button
                const startBtn = document.getElementById('start-simulation-btn');
                if (startBtn) {
                    startBtn.disabled = false;
                }
            }
        } catch (error) {
            console.error('❌ Erreur chargement info simulation:', error);
        }
    }

    async startTransactionAnimation() {
        if (!this.currentTransactionData) {
            console.warn('⚠️  Aucune transaction sélectionnée');
            return;
        }

        console.log(`🎬 Début animation bi-phasée transaction: ${this.currentTransactionData.transaction_id}`);

        // Calculate total steps including bi-phase overhead (resolution + transition + cascade)
        const resolutionSteps = this.currentTransactionData.step_count;
        const transitionSteps = 3; // Fixed transition steps
        const cascadeSteps = 5;    // Fixed cascade steps
        this.totalSteps = resolutionSteps + transitionSteps + cascadeSteps;

        this.currentStep = 0;
        this.animationState = 'playing';

        // Update UI elements
        const maxStepsEl = document.getElementById('max-steps');
        if (maxStepsEl) maxStepsEl.textContent = this.totalSteps;

        // Enable pause/reset buttons
        const pauseButton = document.getElementById('pause-animation');
        const resetButton = document.getElementById('reset-animation');
        if (pauseButton) pauseButton.disabled = false;
        if (resetButton) resetButton.disabled = false;

        // Clear 3D scene
        this.icgs3dCore.clearSimplexVisualization();

        // Start bi-phase animation
        await this.startBiPhaseAnimation();
    }

    async startCompleteSimulation() {
        console.log('🚀 Démarrage simulation complète bi-phasée');

        try {
            // Load simulation data
            this.currentSimulationData = await this.loadCompleteSimulationData();

            if (!this.currentSimulationData || !this.currentSimulationData.success) {
                console.error('❌ Erreur chargement données simulation');
                return;
            }

            const data = this.currentSimulationData;

            // Calculate total steps including bi-phase overhead for all transactions
            const baseSteps = data.total_steps;
            const transactionCount = data.total_transactions;
            const transitionSteps = Math.max(0, transactionCount - 1) * 3; // 3 steps per transition
            const finalCascadeSteps = 8; // Global cascade at end
            this.totalSteps = baseSteps + transitionSteps + finalCascadeSteps;

            // Update simulation control panel
            const totalTransactionsEl = document.getElementById('total-transactions');
            const totalStepsEl = document.getElementById('total-steps');
            const estimatedDurationEl = document.getElementById('estimated-duration');

            if (totalTransactionsEl) totalTransactionsEl.textContent = data.total_transactions;
            if (totalStepsEl) totalStepsEl.textContent = this.totalSteps;
            if (estimatedDurationEl) {
                const enhancedDuration = (data.estimated_duration_ms * 1.5) / 1000; // Account for bi-phase overhead
                estimatedDurationEl.textContent = `${enhancedDuration.toFixed(1)}s`;
            }

            // Update progress elements
            const maxStepsEl = document.getElementById('max-steps');
            if (maxStepsEl) maxStepsEl.textContent = this.totalSteps;

            this.currentStep = 0;
            this.animationState = 'playing';

            // Enable pause/reset buttons
            const pauseButton = document.getElementById('pause-animation');
            const resetButton = document.getElementById('reset-animation');
            if (pauseButton) pauseButton.disabled = false;
            if (resetButton) resetButton.disabled = false;

            // Clear 3D scene
            this.icgs3dCore.clearSimplexVisualization();

            // Start bi-phase simulation animation
            await this.startBiPhaseAnimation();

            console.log(`✅ Simulation bi-phasée lancée: ${data.total_transactions} transactions, ${this.totalSteps} étapes totales`);

        } catch (error) {
            console.error('❌ Erreur lancement simulation bi-phasée:', error);
        }
    }

    animateTransactionSteps(transactionData) {
        console.log(`🎨 Animation étapes transaction: ${transactionData.step_count} étapes`);

        const steps = transactionData.simplex_steps;
        let stepIndex = 0;

        const animateStep = () => {
            if (this.animationState === 'stopped' || stepIndex >= steps.length) {
                return;
            }

            if (this.animationState === 'playing') {
                const step = steps[stepIndex];
                this.visualizeSimplexStep(step, stepIndex, steps.length);

                // Update progress
                this.currentStep = stepIndex + 1;
                document.getElementById('current-animation-step').textContent = this.currentStep;

                stepIndex++;
            }

            // Continue animation
            setTimeout(animateStep, 1000 / this.animationSpeed);
        };

        animateStep();
    }

    animateCompleteSimulation(simulationData) {
        console.log(`🎨 Animation simulation complète: ${simulationData.total_transactions} transactions`);

        let transactionIndex = 0;
        let globalStepIndex = 0;

        const animateTransaction = () => {
            if (this.animationState === 'stopped' || transactionIndex >= simulationData.transactions.length) {
                return;
            }

            const transaction = simulationData.transactions[transactionIndex];
            console.log(`🔄 Animation transaction ${transactionIndex + 1}/${simulationData.transactions.length}: ${transaction.transaction_id}`);

            // Update progress
            document.getElementById('current-tx').textContent = transactionIndex + 1;

            // Animate transaction steps
            const steps = transaction.simplex_steps;
            let stepIndex = 0;

            const animateTransactionStep = () => {
                if (this.animationState === 'stopped') {
                    return;
                }

                if (this.animationState === 'playing' && stepIndex < steps.length) {
                    const step = steps[stepIndex];
                    this.visualizeSimplexStep(step, stepIndex, steps.length);

                    // Update global progress
                    globalStepIndex++;
                    this.currentStep = globalStepIndex;
                    document.getElementById('current-step').textContent = globalStepIndex;
                    document.getElementById('current-animation-step').textContent = globalStepIndex;

                    // Update progress bar
                    const progressPercent = (globalStepIndex / simulationData.total_steps) * 100;
                    document.getElementById('progress-fill').style.width = `${progressPercent}%`;

                    stepIndex++;

                    setTimeout(animateTransactionStep, 800 / this.animationSpeed);
                } else {
                    // Transaction terminée, passer à la suivante
                    transactionIndex++;
                    setTimeout(animateTransaction, 1000 / this.animationSpeed);
                }
            };

            animateTransactionStep();
        };

        animateTransaction();
    }

    visualizeSimplexStep(step, stepIndex, totalSteps) {
        console.log(`🎯 Visualisation étape Simplex ${stepIndex + 1}/${totalSteps}:`, step.coordinates);

        // Create or update point in 3D space
        const geometry = new THREE.SphereGeometry(0.1, 16, 16);
        const material = new THREE.MeshBasicMaterial({
            color: step.is_optimal ? 0x00ff00 : (step.is_feasible ? 0x0088ff : 0xff4444)
        });

        const point = new THREE.Mesh(geometry, material);
        point.position.set(step.coordinates[0], step.coordinates[1], step.coordinates[2]);

        // Add to scene
        this.icgs3dCore.scene.add(point);

        // Create path line to previous step if exists
        if (stepIndex > 0) {
            // Logic for connecting steps with lines would go here
        }

        // Show step info
        this.icgs3dCore.showNotification(
            `Étape ${stepIndex + 1}: ${step.is_optimal ? 'OPTIMAL' : (step.is_feasible ? 'FAISABLE' : 'NON FAISABLE')}`,
            step.is_optimal ? 'success' : 'info'
        );
    }

    togglePlayPause() {
        if (this.animationState === 'playing') {
            this.animationState = 'paused';
            document.getElementById('play-pause-btn').textContent = '▶️';
            console.log('⏸️ Animation en pause');
        } else if (this.animationState === 'paused') {
            this.animationState = 'playing';
            document.getElementById('play-pause-btn').textContent = '⏸️';
            console.log('▶️ Animation reprise');
        }
    }

    stepBack() {
        if (this.currentStep > 0) {
            this.currentStep--;
            document.getElementById('current-animation-step').textContent = this.currentStep;
            console.log(`⏮️ Étape précédente: ${this.currentStep}`);
        }
    }

    stepForward() {
        if (this.currentStep < this.totalSteps) {
            this.currentStep++;
            document.getElementById('current-animation-step').textContent = this.currentStep;
            console.log(`⏭️ Étape suivante: ${this.currentStep}`);
        }
    }

    resetAnimation() {
        this.animationState = 'stopped';
        this.currentStep = 0;

        // Update UI elements
        const currentStepEl = document.getElementById('current-step');
        const progressFill = document.getElementById('progress-fill');

        if (currentStepEl) currentStepEl.textContent = '0';
        if (progressFill) progressFill.style.width = '0%';

        // Reset button states
        const playButton = document.getElementById('play-animation');
        if (playButton) playButton.disabled = this.mode === 'single' && !this.currentTransactionData;

        // Clear 3D visualization
        this.icgs3dCore.clearSimplexVisualization();

        console.log('🔄 Animation reset');
    }

    async selectTransaction(transactionId) {
        console.log(`🎯 Sélection transaction: ${transactionId}`);

        // Update visual selection
        document.querySelectorAll('.transaction-item').forEach(item => {
            item.classList.remove('selected');
        });

        const selectedItem = document.querySelector(`[data-transaction-id="${transactionId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('selected');
        }

        // Load transaction data
        await this.loadTransactionData(transactionId);

        // Update transaction info panel
        this.updateTransactionInfo(transactionId);

        // Enable play button
        const playButton = document.getElementById('play-animation');
        if (playButton) {
            playButton.disabled = false;
        }
    }

    pauseAnimation() {
        console.log('⏸ Pause animation');
        this.animationState = 'paused';

        // Update button states
        const playButton = document.getElementById('play-animation');
        const pauseButton = document.getElementById('pause-animation');

        if (playButton) playButton.disabled = false;
        if (pauseButton) pauseButton.disabled = true;

        // Stop any running animation intervals
        if (this.currentAnimation) {
            clearInterval(this.currentAnimation);
            this.currentAnimation = null;
        }
    }

    updateTransactionInfo(transactionId) {
        const infoPanel = document.getElementById('selected-transaction-info');
        if (!infoPanel || !this.currentTransactionData) return;

        const data = this.currentTransactionData;
        infoPanel.innerHTML = `
            <div class="selected-transaction-details">
                <h5>Transaction: ${transactionId}</h5>
                <div class="detail-row">
                    <span class="label">Étapes Simplex:</span>
                    <span class="value">${data.step_count}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Durée estimée:</span>
                    <span class="value">${data.estimated_duration_ms}ms</span>
                </div>
                <div class="detail-row">
                    <span class="label">Complexité:</span>
                    <span class="value complexity-${data.complexity.toLowerCase()}">${data.complexity}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Flux:</span>
                    <span class="value">${data.source_account} → ${data.target_account}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Montant:</span>
                    <span class="value">${data.amount || 'N/A'}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Faisable:</span>
                    <span class="value ${data.feasible ? 'feasible' : 'not-feasible'}">
                        ${data.feasible ? '✅ Oui' : '❌ Non'}
                    </span>
                </div>
            </div>
        `;

        // Update progress info
        const maxStepsEl = document.getElementById('max-steps');
        if (maxStepsEl) maxStepsEl.textContent = data.step_count;
    }

    // ======================================
    // BI-PHASE ANIMATION IMPLEMENTATION
    // ======================================

    setAnimationPhase(phase) {
        console.log(`🔄 Changement phase animation: ${phase}`);
        this.currentPhase = phase;

        // Update phase indicator
        const phaseIndicator = document.getElementById('current-phase');
        if (phaseIndicator) {
            phaseIndicator.textContent = phase;
        }

        // Show/hide phase information panels
        const phaseInfos = ['resolution-phase-info', 'transition-phase-info', 'cascade-phase-info'];
        phaseInfos.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.style.display = 'none';
            }
        });

        // Show current phase info
        const currentPhaseInfo = document.getElementById(`${phase.toLowerCase()}-phase-info`);
        if (currentPhaseInfo) {
            currentPhaseInfo.style.display = 'block';
        }

        // Update 3D axis configuration based on phase
        this.update3DAxisMapping(phase);
    }

    update3DAxisMapping(phase) {
        console.log(`🎯 Mise à jour mapping axes 3D pour phase: ${phase}`);

        // Store current axis configuration for 3D visualization
        switch (phase) {
            case 'Résolution':
                this.current3DAxes = {
                    x: 'flux_transaction',
                    y: 'flux_compte_origine',
                    z: 'flux_redistribue'
                };
                break;
            case 'Transition':
                this.current3DAxes = {
                    x: 'impact_cascade',
                    y: 'flux_comptes_cibles',
                    z: 'amplitude_perturbation'
                };
                break;
            case 'Cascade':
                this.current3DAxes = {
                    x: 'propagation_intersectorielle',
                    y: 'magnitude_impact',
                    z: 'stabilite_reseau'
                };
                break;
        }

        // Update 3D scene axis labels if needed
        this.updateAxisLabels();
    }

    updateAxisLabels() {
        // TODO: Implementation for updating 3D axis labels in Three.js scene
        console.log('📊 Mise à jour labels axes 3D:', this.current3DAxes);
    }

    async startBiPhaseAnimation() {
        console.log('🎬 Démarrage animation bi-phasée');
        this.animationState = 'playing';

        if (this.mode === 'single') {
            await this.runSingleTransactionBiPhase();
        } else {
            await this.runCompleteSimulationBiPhase();
        }
    }

    async runSingleTransactionBiPhase() {
        console.log('🎯 Animation bi-phasée transaction unique');

        if (!this.currentTransactionData) {
            console.error('❌ Pas de données transaction pour animation');
            return;
        }

        // Phase 1: Résolution Simplex
        this.setAnimationPhase('Résolution');
        await this.animateResolutionPhase(this.currentTransactionData);

        // Phase 2: Transition (impact cascade)
        if (this.animationState === 'playing') {
            this.setAnimationPhase('Transition');
            await this.animateTransitionPhase(this.currentTransactionData);
        }

        // Phase 3: Cascade globale
        if (this.animationState === 'playing') {
            this.setAnimationPhase('Cascade');
            await this.animateCascadePhase(this.currentTransactionData);
        }

        console.log('✅ Animation bi-phasée transaction terminée');
        this.animationState = 'stopped';
    }

    async runCompleteSimulationBiPhase() {
        console.log('🎬 Animation bi-phasée simulation complète');

        // Load complete simulation data
        const simulationData = await this.loadCompleteSimulationData();
        if (!simulationData || !simulationData.success) {
            console.error('❌ Impossible de charger données simulation');
            return;
        }

        let globalStepIndex = 0;
        const totalSteps = simulationData.total_steps;

        // Iterate through each transaction with bi-phase animation
        for (let txIndex = 0; txIndex < simulationData.transactions.length && this.animationState === 'playing'; txIndex++) {
            const transaction = simulationData.transactions[txIndex];

            console.log(`🔄 Animation transaction ${txIndex + 1}/${simulationData.transactions.length}: ${transaction.transaction_id}`);

            // Phase 1: Résolution pour cette transaction
            this.setAnimationPhase('Résolution');
            const resolutionSteps = await this.animateResolutionPhase(transaction, globalStepIndex, totalSteps);
            globalStepIndex += resolutionSteps;

            // Phase 2: Transition vers transaction suivante
            if (txIndex < simulationData.transactions.length - 1 && this.animationState === 'playing') {
                this.setAnimationPhase('Transition');
                const transitionSteps = await this.animateTransitionToNext(transaction, simulationData.transactions[txIndex + 1]);
                globalStepIndex += transitionSteps;
            }

            // Update global progress
            this.updateGlobalProgress(globalStepIndex, totalSteps);
        }

        // Phase finale: Cascade globale
        if (this.animationState === 'playing') {
            this.setAnimationPhase('Cascade');
            await this.animateFinalCascade(simulationData);
        }

        console.log('✅ Animation bi-phasée simulation complète terminée');
        this.animationState = 'stopped';
    }

    async animateResolutionPhase(transactionData, globalStepIndex = 0, totalSteps = null) {
        console.log(`🎯 Animation phase résolution pour ${transactionData.transaction_id || transactionData.id}`);

        const steps = transactionData.simplex_steps || [];
        let stepCount = 0;

        for (let i = 0; i < steps.length && this.animationState === 'playing'; i++) {
            const step = steps[i];

            // Visualize current step with resolution axis mapping
            this.visualizeResolutionStep(step, i, steps.length);

            // Update progress
            stepCount++;
            this.currentStep = globalStepIndex + stepCount;
            this.updateProgressDisplay(this.currentStep, totalSteps || steps.length);

            // Wait according to animation speed
            await this.waitForAnimationSpeed();
        }

        return stepCount;
    }

    async animateTransitionPhase(transactionData) {
        console.log(`🔄 Animation phase transition pour ${transactionData.transaction_id || transactionData.id}`);

        // Simulate transition steps (cascade effects)
        const transitionSteps = 3; // Fixed number of transition visualization steps

        for (let i = 0; i < transitionSteps && this.animationState === 'playing'; i++) {
            // Visualize cascade effects with transition axis mapping
            this.visualizeTransitionStep(transactionData, i, transitionSteps);

            // Update progress
            this.currentStep++;
            this.updateProgressDisplay(this.currentStep, this.totalSteps);

            await this.waitForAnimationSpeed(800); // Slower transition animation
        }

        return transitionSteps;
    }

    async animateCascadePhase(transactionData) {
        console.log(`🌊 Animation phase cascade pour ${transactionData.transaction_id || transactionData.id}`);

        // Simulate global cascade visualization
        const cascadeSteps = 5; // Fixed number of cascade visualization steps

        for (let i = 0; i < cascadeSteps && this.animationState === 'playing'; i++) {
            // Visualize global economic impact with cascade axis mapping
            this.visualizeCascadeStep(transactionData, i, cascadeSteps);

            // Update progress
            this.currentStep++;
            this.updateProgressDisplay(this.currentStep, this.totalSteps);

            await this.waitForAnimationSpeed(1000); // Slowest cascade animation
        }

        return cascadeSteps;
    }

    visualizeResolutionStep(step, stepIndex, totalSteps) {
        console.log(`🎯 Visualisation étape résolution ${stepIndex + 1}/${totalSteps}:`, step.coordinates);

        // Use resolution axis mapping (flux_transaction, flux_compte_origine, flux_redistribue)
        const position = {
            x: step.coordinates[0], // Flux dans transaction
            y: step.coordinates[1], // Flux restant sur compte origine
            z: step.coordinates[2]  // Flux redistribué
        };

        // Visualize in 3D scene with resolution colors (blue/green tones)
        this.visualizeStepIn3D(position, stepIndex, 'resolution', 0x2196F3);
    }

    visualizeTransitionStep(transactionData, stepIndex, totalSteps) {
        console.log(`🔄 Visualisation étape transition ${stepIndex + 1}/${totalSteps}`);

        // Simulate transition coordinates based on cascade effects
        const position = {
            x: stepIndex * 0.5,     // Impact cascade sortante
            y: stepIndex * 0.3,     // Flux redistribué vers comptes cibles
            z: stepIndex * 0.2      // Amplitude perturbation économique
        };

        // Visualize with transition colors (orange tones)
        this.visualizeStepIn3D(position, stepIndex, 'transition', 0xFF9800);
    }

    visualizeCascadeStep(transactionData, stepIndex, totalSteps) {
        console.log(`🌊 Visualisation étape cascade ${stepIndex + 1}/${totalSteps}`);

        // Simulate cascade coordinates for global impact
        const position = {
            x: Math.sin(stepIndex) * 2,  // Propagation inter-sectorielle
            y: stepIndex * 0.4,          // Magnitude impact économique
            z: 1 - stepIndex * 0.1       // Stabilité réseau post-transaction
        };

        // Visualize with cascade colors (red/purple tones)
        this.visualizeStepIn3D(position, stepIndex, 'cascade', 0xF44336);
    }

    visualizeStepIn3D(position, stepIndex, phase, color) {
        // Create or update 3D visualization in Three.js scene
        // This integrates with the existing Three.js infrastructure

        // Remove previous step visualization
        this.icgs3dCore.clearSimplexVisualization();

        // Create step visualization object
        const geometry = new THREE.SphereGeometry(0.1, 16, 16);
        const material = new THREE.MeshBasicMaterial({ color: color });
        const stepSphere = new THREE.Mesh(geometry, material);

        stepSphere.position.set(position.x, position.y, position.z);
        stepSphere.userData = { type: 'simplex_step', phase: phase, step: stepIndex };

        // Add to scene
        ICGS3DApp.scene.add(stepSphere);

        // Add trail effect for path visualization
        this.addTrailEffect(position, phase, stepIndex);
    }

    addTrailEffect(position, phase, stepIndex) {
        // Create trail line connecting previous positions
        // TODO: Implement trail line geometry for path visualization
        console.log(`✨ Effet trail phase ${phase} étape ${stepIndex}:`, position);
    }

    async waitForAnimationSpeed(baseDelay = 500) {
        const delay = baseDelay / this.animationSpeed;
        return new Promise(resolve => setTimeout(resolve, delay));
    }

    updateProgressDisplay(currentStep, totalSteps) {
        const currentStepEl = document.getElementById('current-step');
        const progressFill = document.getElementById('progress-fill');

        if (currentStepEl) currentStepEl.textContent = currentStep;

        if (progressFill && totalSteps) {
            const progressPercent = (currentStep / totalSteps) * 100;
            progressFill.style.width = `${progressPercent}%`;
        }
    }

    updateGlobalProgress(currentStep, totalSteps) {
        this.currentStep = currentStep;
        this.updateProgressDisplay(currentStep, totalSteps);

        console.log(`📊 Progression globale: ${currentStep}/${totalSteps} (${((currentStep/totalSteps)*100).toFixed(1)}%)`);
    }

    async loadCompleteSimulationData() {
        console.log('📋 Chargement données simulation complète');

        try {
            const response = await fetch('/api/simplex_3d/simulation/run', { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                console.log(`✅ Données simulation chargées: ${data.total_transactions} transactions`);
                return data;
            } else {
                console.error('❌ Erreur API simulation:', data.error);
                return null;
            }
        } catch (error) {
            console.error('❌ Erreur réseau chargement simulation:', error);
            return null;
        }
    }

    async animateTransitionToNext(currentTransaction, nextTransaction) {
        console.log(`🔄 Animation transition: ${currentTransaction.transaction_id} → ${nextTransaction.transaction_id}`);

        // Simulate transition animation between transactions
        const transitionSteps = 3;

        for (let i = 0; i < transitionSteps && this.animationState === 'playing'; i++) {
            // Create transition visualization
            const position = {
                x: i * 0.4,
                y: Math.sin(i) * 0.3,
                z: i * 0.2
            };

            this.visualizeStepIn3D(position, i, 'transition', 0xFF9800);

            await this.waitForAnimationSpeed(600);
        }

        return transitionSteps;
    }

    async animateFinalCascade(simulationData) {
        console.log('🌊 Animation cascade finale globale');

        // Simulate final global cascade
        const cascadeSteps = 8;

        for (let i = 0; i < cascadeSteps && this.animationState === 'playing'; i++) {
            const position = {
                x: Math.cos(i * 0.5) * 2,
                y: Math.sin(i * 0.5) * 2,
                z: i * 0.3
            };

            this.visualizeStepIn3D(position, i, 'cascade', 0xF44336);

            await this.waitForAnimationSpeed(1200);
        }

        return cascadeSteps;
    }
}

// Extension ICGS3DCore pour Simplex
ICGS3DCore.prototype.clearSimplexVisualization = function() {
    console.log('🧹 Nettoyage visualisation Simplex');

    // Remove Simplex-specific objects from scene
    const objectsToRemove = [];
    this.scene.traverse((child) => {
        if (child.userData && child.userData.type === 'simplex_step') {
            objectsToRemove.push(child);
        }
    });

    objectsToRemove.forEach(obj => this.scene.remove(obj));
};

// ======================================
// INITIALISATION APPLICATION
// ======================================
document.addEventListener('DOMContentLoaded', () => {
    window.icgs3dApp = new ICGS3DCore();

    // Initialize Simplex Animation Controller
    window.icgs3dApp.simplexController = new SimplexAnimationController(window.icgs3dApp);
});