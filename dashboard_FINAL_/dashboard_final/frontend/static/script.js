
        console.log(' Dashboard démarré');

        let currentData = { pib: null, inflation: null, opec: null, pibSecteurs: null };
        let chartInstances = {};

        const SECTEUR_GROUPS = {
            'Agriculture & Pêche': ['agriculture', 'pêche', 'peche', 'agricole'],
            'Hydrocarbures': ['hydrocarbure', 'pétrole', 'petrole', 'gaz', 'extraction'],
            'Industrie Manufacturière': ['industrie', 'manufacturière', 'manufacturiere', 'textile', 'agroalimentaire',
                'cuir', 'chaussure', 'bois', 'papier', 'chimique', 'caoutchouc', 'plastique',
                'minéraux', 'mineraux', 'métallurgie', 'metallurgie', 'mécanique', 'mecanique',
                'électronique', 'electronique', 'équipement', 'equipement'],
            'BTP & Construction': ['construction', 'btp', 'bâtiment', 'batiment', 'travaux'],
            'Services Marchands': ['commerce', 'hôtel', 'hotel', 'restaurant', 'transport', 'communication',
                'financier', 'financière', 'financiere', 'immobilier'],
            'Services Non Marchands': ['administration', 'publique', 'éducation', 'education', 'santé', 'sante',
                'social', 'collectif']
        };

        function categorizeSector(secteurName) {
            if (!secteurName) return 'Autres';
            const lowerName = secteurName.toLowerCase();
            for (const [category, keywords] of Object.entries(SECTEUR_GROUPS)) {
                if (keywords.some(keyword => lowerName.includes(keyword))) {
                    return category;
                }
            }
            return 'Autres';
        }

        function destroyChart(chartId) {
            if (chartInstances[chartId]) {
                try {
                    chartInstances[chartId].destroy();
                    delete chartInstances[chartId];
                } catch(e) {
                    console.error('Erreur destruction:', e);
                }
            }
        }

        function destroyAllCharts() {
            Object.keys(chartInstances).forEach(id => destroyChart(id));
        }

        async function loadAllData() {
            try {
                console.log(' Chargement des données...');
                
                const [pibResp, inflationResp, opecResp, secteursResp] = await Promise.all([
                    fetch('/api/query/croissance-pib'),
                    fetch('/api/query/inflation'),
                    fetch('/api/query/opec'),
                    fetch('/api/table/pib_secteurs')
                ]);

                if (!pibResp.ok || !inflationResp.ok || !opecResp.ok) {
                    throw new Error('Erreur réponse API');
                }

                currentData.pib = await pibResp.json();
                currentData.inflation = await inflationResp.json();
                currentData.opec = await opecResp.json();
                currentData.pibSecteurs = await secteursResp.json();

                console.log(' Données chargées');
                return true;
            } catch (error) {
                console.error(' Erreur:', error);
                return false;
            }
        }

        function loadPage(page) {
            console.log(' Page:', page);
            
            destroyAllCharts();
            
            document.querySelectorAll('.nav-buttons a').forEach(a => a.classList.remove('active'));
            const navBtn = document.getElementById(`nav-${page}`);
            if (navBtn) navBtn.classList.add('active');

            document.getElementById('loading').style.display = 'block';
            document.getElementById('content').innerHTML = '';

            setTimeout(() => {
                try {
                    switch(page) {
                        case 'vue-ensemble': renderVueEnsemble(); break;
                        case 'pib': renderPIB(); break;
                        case 'inflation': renderInflation(); break;
                        case 'petrole': renderPetrole(); break;
                        case 'analyse': renderAnalyse(); break;
                        default: document.getElementById('content').innerHTML = '<div class="info-box"><h2> Page non trouvée</h2></div>';
                    }
                } catch(e) {
                    console.error(' Erreur:', e);
                    document.getElementById('content').innerHTML = `<div class="info-box"><h2> Erreur: ${e.message}</h2></div>`;
                }
                document.getElementById('loading').style.display = 'none';
            }, 300);
        }

        function calculateStats(values) {
            if (!values || values.length === 0) {
                return { moyenne: 0, max: 0, min: 0, last: 0 };
            }
            return {
                moyenne: values.reduce((a,b) => a+b, 0) / values.length,
                max: Math.max(...values),
                min: Math.min(...values),
                last: values[values.length - 1]
            };
        }

        function normalize(arr) {
            const min = Math.min(...arr);
            const max = Math.max(...arr);
            if (max === min) return arr.map(() => 50);
            return arr.map(v => ((v - min) / (max - min)) * 100);
        }

        function createChart(canvasId, config) {
            try {
                const canvas = document.getElementById(canvasId);
                if (!canvas) {
                    console.error(' Canvas non trouvé:', canvasId);
                    return null;
                }

                const ctx = canvas.getContext('2d');
                destroyChart(canvasId);

                chartInstances[canvasId] = new Chart(ctx, config);
                console.log(' Graphique créé:', canvasId);
                return chartInstances[canvasId];
            } catch(e) {
                console.error(' Erreur graphique:', canvasId, e);
                return null;
            }
        }

        // ===== PAGE 1: VUE D'ENSEMBLE =====
        function renderVueEnsemble() {
            document.getElementById('pageSubtitle').textContent = 
                'Synthèse des indicateurs économiques de l\'Algérie';

            const { pib, inflation, opec } = currentData;

            document.getElementById('content').innerHTML = `
                <div class="info-box">
                    <h2> Question 1: Quelles sont les performances économiques de l'Algérie sur les 20 dernières années ?</h2>
                    <p>Cette vue d'ensemble présente les statistiques clés et compare les performances de trois indicateurs majeurs : 
                    PIB, inflation et prix du pétrole.</p>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <h3> Croissance du PIB</h3>
                        <div class="value">${pib.valeurs[pib.valeurs.length-1].toFixed(2)}%</div>
                        <div class="subtitle">Dernière année (${pib.annees[pib.annees.length-1]})</div>
                    </div>
                    <div class="stat-card">
                        <h3> Inflation (IPC)</h3>
                        <div class="value">${inflation.valeurs[inflation.valeurs.length-1].toFixed(2)}%</div>
                        <div class="subtitle">Taux actuel (${inflation.annees[inflation.annees.length-1]})</div>
                    </div>
                    <div class="stat-card">
                        <h3> Prix Pétrole</h3>
                        <div class="value">$${opec.valeurs[opec.valeurs.length-1].toFixed(2)}</div>
                        <div class="subtitle">Prix OPEC (${opec.annees[opec.annees.length-1]})</div>
                    </div>
                    <div class="stat-card">
                        <h3> Période</h3>
                        <div class="value">${Math.min(...pib.annees.map(a => parseInt(a)))}-${Math.max(...pib.annees.map(a => parseInt(a)))}</div>
                        <div class="subtitle">${pib.annees.length} années</div>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> Moyennes par Décennie</h2>
                    <p>Comparaison des moyennes des trois indicateurs sur différentes périodes</p>
                    <div class="chart-container">
                        <canvas id="decadeChart"></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> Volatilité des Indicateurs</h2>
                    <p>Écart-type mesurant l'instabilité de chaque indicateur (plus c'est élevé, plus c'est volatile)</p>
                    <div class="chart-container">
                        <canvas id="volatilityChart"></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> Années Record</h2>
                    <p>Meilleures et pires performances pour chaque indicateur</p>
                    <div class="chart-container">
                        <canvas id="recordsChart"></canvas>
                    </div>
                </div>
            `;
            
            setTimeout(() => {
                const decades = {
                    '2002-2009': { pib: [], inflation: [], opec: [] },
                    '2010-2019': { pib: [], inflation: [], opec: [] },
                    '2020-2024': { pib: [], inflation: [], opec: [] }
                };

                pib.annees.forEach((annee, idx) => {
                    const year = parseInt(annee);
                    let period = '';
                    if (year <= 2009) period = '2002-2009';
                    else if (year <= 2019) period = '2010-2019';
                    else period = '2020-2024';

                    decades[period].pib.push(pib.valeurs[idx]);
                    
                    const infIdx = inflation.annees.indexOf(annee);
                    if (infIdx !== -1) decades[period].inflation.push(inflation.valeurs[infIdx]);
                    
                    const opecIdx = opec.annees.indexOf(annee);
                    if (opecIdx !== -1) decades[period].opec.push(opec.valeurs[opecIdx]);
                });

                const decadeLabels = Object.keys(decades);
                const pibAvgs = decadeLabels.map(p => decades[p].pib.length > 0 ? 
                    decades[p].pib.reduce((a,b) => a+b) / decades[p].pib.length : 0);
                const infAvgs = decadeLabels.map(p => decades[p].inflation.length > 0 ? 
                    decades[p].inflation.reduce((a,b) => a+b) / decades[p].inflation.length : 0);
                const opecAvgs = decadeLabels.map(p => decades[p].opec.length > 0 ? 
                    decades[p].opec.reduce((a,b) => a+b) / decades[p].opec.length : 0);

                createChart('decadeChart', {
                    type: 'bar',
                    data: {
                        labels: decadeLabels,
                        datasets: [
                            {
                                label: 'PIB Moyen (%)',
                                data: pibAvgs,
                                backgroundColor: '#667eea',
                                yAxisID: 'y'
                            },
                            {
                                label: 'Inflation Moyenne (%)',
                                data: infAvgs,
                                backgroundColor: '#f5576c',
                                yAxisID: 'y'
                            },
                            {
                                label: 'Pétrole Moyen ($/10)',
                                data: opecAvgs.map(v => v/10),
                                backgroundColor: '#43e97b',
                                yAxisID: 'y'
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: true, position: 'top' },
                            tooltip: {
                                callbacks: {
                                    label: (context) => {
                                        let label = context.dataset.label || '';
                                        let value = context.parsed.y;
                                        if (label.includes('Pétrole')) {
                                            value = value * 10;
                                            return `${label}: $${value.toFixed(2)}`;
                                        }
                                        return `${label}: ${value.toFixed(2)}%`;
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: { display: true, text: 'Valeur (%)' }
                            }
                        }
                    }
                });

                function calculateStdDev(arr) {
                    const mean = arr.reduce((a, b) => a + b) / arr.length;
                    const variance = arr.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / arr.length;
                    return Math.sqrt(variance);
                }

                const pibStd = calculateStdDev(pib.valeurs);
                const infStd = calculateStdDev(inflation.valeurs);
                const opecStd = calculateStdDev(opec.valeurs);

                createChart('volatilityChart', {
                    type: 'bar',
                    data: {
                        labels: ['PIB', 'Inflation', 'Pétrole'],
                        datasets: [{
                            label: 'Volatilité (écart-type)',
                            data: [pibStd, infStd, opecStd],
                            backgroundColor: ['#667eea', '#f5576c', '#43e97b']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: (context) => {
                                        return `Volatilité: ${context.parsed.y.toFixed(2)}`;
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: { display: true, text: 'Écart-type' }
                            }
                        }
                    }
                });

                const pibStats = calculateStats(pib.valeurs);
                const infStats = calculateStats(inflation.valeurs);
                const opecStats = calculateStats(opec.valeurs);

                createChart('recordsChart', {
                    type: 'bar',
                    data: {
                        labels: ['PIB', 'Inflation', 'Pétrole'],
                        datasets: [
                            {
                                label: 'Maximum',
                                data: [pibStats.max, infStats.max, opecStats.max],
                                backgroundColor: '#27ae60'
                            },
                            {
                                label: 'Moyenne',
                                data: [pibStats.moyenne, infStats.moyenne, opecStats.moyenne],
                                backgroundColor: '#95a5a6'
                            },
                            {
                                label: 'Minimum',
                                data: [pibStats.min, infStats.min, opecStats.min],
                                backgroundColor: '#e74c3c'
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: true, position: 'top' }
                        },
                        scales: {
                            y: {
                                beginAtZero: false,
                                title: { display: true, text: 'Valeur' }
                            }
                        }
                    }
                });
            }, 100);
        }

        // ===== PAGE 2: PIB =====
        function renderPIB() {
            document.getElementById('pageSubtitle').textContent = 
                'Analyse de la croissance du Produit Intérieur Brut par secteur';

            const { pib, pibSecteurs } = currentData;
            const stats = calculateStats(pib.valeurs);

            document.getElementById('content').innerHTML = `
                <div class="info-box">
                    <h2> Question 2: Quelle est l'évolution du PIB en Algérie ?</h2>
                    <p>Analyse de l'évolution de la croissance du PIB par grandes catégories économiques.</p>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <h3> Croissance Moyenne</h3>
                        <div class="value">${stats.moyenne.toFixed(2)}%</div>
                        <div class="subtitle">Sur toute la période</div>
                    </div>
                    <div class="stat-card">
                        <h3> Maximum</h3>
                        <div class="value">${stats.max.toFixed(2)}%</div>
                        <div class="subtitle">Plus forte croissance</div>
                    </div>
                    <div class="stat-card">
                        <h3> Minimum</h3>
                        <div class="value">${stats.min.toFixed(2)}%</div>
                        <div class="subtitle">Plus faible croissance</div>
                    </div>
                    <div class="stat-card">
                        <h3> Dernière Année</h3>
                        <div class="value">${stats.last.toFixed(2)}%</div>
                        <div class="subtitle">${pib.annees[pib.annees.length-1]}</div>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> Évolution de la Croissance du PIB (${pib.annees[0]} - ${pib.annees[pib.annees.length-1]})</h2>
                    <div class="chart-container">
                        <canvas id="pibChart"></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> Comparaison par Période</h2>
                    <div class="chart-container">
                        <canvas id="pibBarChart"></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> Répartition du PIB par Grand Secteur</h2>
                    <p>Contribution des grandes catégories économiques au PIB algérien (année la plus récente)</p>
                    <div class="chart-container">
                        <canvas id="secteursPieChart"></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> Croissance par Grand Secteur (3 dernières années)</h2>
                    <p>Évolution de la croissance de chaque grande catégorie économique</p>
                    <div class="chart-container">
                        <canvas id="secteursBarChart"></canvas>
                    </div>
                </div>
            `;

            setTimeout(() => {
                createChart('pibChart', {
                    type: 'line',
                    data: {
                        labels: pib.annees,
                        datasets: [{
                            label: 'Croissance du PIB (%)',
                            data: pib.valeurs,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 3,
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: { ticks: { callback: (value) => value.toFixed(1) + '%' }}
                        }
                    }
                });

                const periods = { '2002-2009': [], '2010-2019': [], '2020-2025': [] };
                pib.annees.forEach((annee, idx) => {
                    const year = parseInt(annee);
                    if (year <= 2009) periods['2002-2009'].push(pib.valeurs[idx]);
                    else if (year <= 2019) periods['2010-2019'].push(pib.valeurs[idx]);
                    else periods['2020-2025'].push(pib.valeurs[idx]);
                });

                const avgPeriods = Object.keys(periods).map(p => 
                    periods[p].length > 0 ? periods[p].reduce((a,b) => a+b, 0) / periods[p].length : 0
                );

                createChart('pibBarChart', {
                    type: 'bar',
                    data: {
                        labels: Object.keys(periods),
                        datasets: [{
                            label: 'Croissance moyenne (%)',
                            data: avgPeriods,
                            backgroundColor: ['#667eea', '#764ba2', '#f093fb']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }}
                    }
                });

                if (pibSecteurs && pibSecteurs.length > 0) {
                    const lastYearCol = Object.keys(pibSecteurs[0])
                        .filter(k => k.startsWith('annee_'))
                        .sort()
                        .pop();
                    
const groupedData = {};
const groupedCounts = {};  // 🆕 Compteur pour moyenne

    pibSecteurs.forEach(row => {
    if (row.secteur && !row.secteur.includes('Produit Intérieur Brut')) {
        const category = categorizeSector(row.secteur);
        const value = parseFloat(row[lastYearCol]) || 0;
        
        if (!groupedData[category]) {
            groupedData[category] = 0;
            groupedCounts[category] = 0;  // 🆕 Initialiser compteur
        }
        groupedData[category] += value;
        groupedCounts[category]++;  // 🆕 Incrémenter compteur
    }
});

// 🆕 CALCULER LES MOYENNES
Object.keys(groupedData).forEach(category => {
    if (groupedCounts[category] > 0) {
        groupedData[category] = groupedData[category] / groupedCounts[category];
    }
});                    

                    const categoryNames = Object.keys(groupedData);
                    const categoryValues = Object.values(groupedData);
                    const colors = ['#43e97b', '#ff6b6b', '#667eea', '#ffd93d', '#f093fb', '#51cf66', '#95a5a6'];

                    createChart('secteursPieChart', {
                        type: 'pie',
                        data: {
                            labels: categoryNames,
                            datasets: [{
                                data: categoryValues,
                                backgroundColor: colors.slice(0, categoryNames.length)
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { 
                                    position: 'right',
                                    labels: {
                                        font: { size: 14 },
                                        padding: 15
                                    }
                                },
                                tooltip: {
                                    callbacks: {
                                        label: (context) => {
                                            const label = context.label || '';
                                            const value = context.parsed || 0;
                                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                            const percentage = ((value / total) * 100).toFixed(1);
                                            return `${label}: ${value.toFixed(2)}% (${percentage}% du total)`;
                                        }
                                    }
                                }
                            }
                        }
                    });

                    const yearCols = Object.keys(pibSecteurs[0])
                        .filter(k => k.startsWith('annee_'))
                        .sort()
                        .slice(-3);
                    
                    const datasets = yearCols.map((col, idx) => {
    const yearGroupedData = {};
    const yearGroupedCounts = {};  // 🆕 Compteur pour moyenne
    
    pibSecteurs.forEach(row => {
        if (row.secteur && !row.secteur.includes('Produit Intérieur Brut')) {
            const category = categorizeSector(row.secteur);
            const value = parseFloat(row[col]) || 0;
            
            if (!yearGroupedData[category]) {
                yearGroupedData[category] = 0;
                yearGroupedCounts[category] = 0;  // 🆕 Initialiser compteur
            }
            yearGroupedData[category] += value;
            yearGroupedCounts[category]++;  // 🆕 Incrémenter compteur
        }
    });
    
    // 🆕 CALCULER LES MOYENNES
    Object.keys(yearGroupedData).forEach(category => {
        if (yearGroupedCounts[category] > 0) {
            yearGroupedData[category] = yearGroupedData[category] / yearGroupedCounts[category];
        }
    });
    
    return {
        label: col.replace('annee_', ''),
        data: categoryNames.map(cat => yearGroupedData[cat] || 0),
        backgroundColor: colors[idx % colors.length]
    };
});

                    createChart('secteursBarChart', {
                        type: 'bar',
                        data: {
                            labels: categoryNames,
                            datasets: datasets
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: true, position: 'top' }
                            },
                            scales: {
                                x: {
                                    ticks: { 
                                        maxRotation: 45, 
                                        minRotation: 45,
                                        font: { size: 12 }
                                    }
                                },
                                y: {
                                    ticks: { callback: (value) => value.toFixed(1) + '%' }
                                }
                            }
                        }
                    });
                }
            }, 100);
        }

        // ===== PAGE 3: INFLATION =====
        function renderInflation() {
            const { inflation } = currentData;
            const stats = calculateStats(inflation.valeurs);

            document.getElementById('content').innerHTML = `
                <div class="info-box">
                    <h2> Question 3: Quelle est l'évolution de l'inflation et son impact sur le pouvoir d'achat ?</h2>
                    <p>L'inflation mesure l'augmentation des prix. Un taux élevé réduit le pouvoir d'achat des citoyens.</p>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <h3> Moyenne</h3>
                        <div class="value">${stats.moyenne.toFixed(2)}%</div>
                        <div class="subtitle">Sur toute la période</div>
                    </div>
                    <div class="stat-card">
                        <h3> Maximum</h3>
                        <div class="value">${stats.max.toFixed(2)}%</div>
                        <div class="subtitle">Pic d'inflation</div>
                    </div>
                    <div class="stat-card">
                        <h3> Minimum</h3>
                        <div class="value">${stats.min.toFixed(2)}%</div>
                        <div class="subtitle">Plus bas niveau</div>
                    </div>
                    <div class="stat-card">
                        <h3> Actuel</h3>
                        <div class="value">${stats.last.toFixed(2)}%</div>
                        <div class="subtitle">${inflation.annees[inflation.annees.length-1]}</div>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> Évolution de l'Inflation (IPC)</h2>
                    <p>Indice des Prix à la Consommation : mesure l'évolution du coût de la vie</p>
                    <div class="chart-container">
                        <canvas id="inflationChart"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <h2> Impact sur le Pouvoir d'Achat</h2>
                    <p>Évolution de la valeur de 100 DA sur 20 ans (base 2004 = 100 DA) <strong>  Formule: Pouvoir d'Achat(année n) = Pouvoir d'Achat(année n-1) ÷ (1 + Taux d'Inflation)</strong></p>
                    <div class="chart-container">
                        <canvas id="powerChart"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <h2> Inflation par Période</h2>
                    <p>Comparaison de l'inflation moyenne sur différentes décennies</p>
                    <div class="chart-container">
                        <canvas id="inflationPeriodChart"></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> TOP 5 Années de Forte Inflation</h2>
                    <p>Les années où l'inflation a été la plus élevée</p>
                    <div class="chart-container">
                        <canvas id="topInflationChart"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <h2> Inflation pendant les Crises</h2>
                    <p>Impact des crises économiques majeures sur l'inflation</p>
                    <div class="chart-container">
                        <canvas id="crisisChart"></canvas>
                    </div>
                </div>

                
            `;

            setTimeout(() => {
                createChart('inflationChart', {
                    type: 'line',
                    data: {
                        labels: inflation.annees,
                        datasets: [{
                            label: 'Inflation (%)',
                            data: inflation.valeurs,
                            borderColor: '#f5576c',
                            backgroundColor: 'rgba(245, 87, 108, 0.1)',
                            borderWidth: 3,
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false
                    }
                });

                const periods = { '2004-2009': [], '2010-2019': [], '2020-2025': [] };
                inflation.annees.forEach((annee, idx) => {
                    const year = parseInt(annee);
                    if (year <= 2009) periods['2004-2009'].push(inflation.valeurs[idx]);
                    else if (year <= 2019) periods['2010-2019'].push(inflation.valeurs[idx]);
                    else periods['2020-2025'].push(inflation.valeurs[idx]);
                });

                const avgPeriods = Object.keys(periods).map(p => 
                    periods[p].length > 0 ? periods[p].reduce((a,b) => a+b, 0) / periods[p].length : 0
                );

                createChart('inflationPeriodChart', {
                    type: 'bar',
                    data: {
                        labels: Object.keys(periods),
                        datasets: [{
                            label: 'Inflation moyenne (%)',
                            data: avgPeriods,
                            backgroundColor: ['#f5576c', '#ff6b6b', '#f093fb']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }}
                    }
                });

                const crisisYears = ['2008', '2020', '2022', '2023'];
                const crisisData = crisisYears.map(year => {
                    const idx = inflation.annees.indexOf(year);
                    return idx !== -1 ? inflation.valeurs[idx] : 0;
                });

                createChart('crisisChart', {
                    type: 'bar',
                    data: {
                        labels: ['Crise 2008', 'COVID 2020', 'Ukraine 2022', '2023'],
                        datasets: [{
                            label: 'Inflation (%)',
                            data: crisisData,
                            backgroundColor: ['#f093fb', '#ffd93d', '#ff6b6b', '#f5576c']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }}
                    }
                });

                const topInflation = inflation.annees
                    .map((annee, idx) => ({ annee, valeur: inflation.valeurs[idx] }))
                    .sort((a, b) => b.valeur - a.valeur)
                    .slice(0, 5);

                createChart('topInflationChart', {
                    type: 'bar',
                    data: {
                        labels: topInflation.map(d => d.annee),
                        datasets: [{
                            label: 'Inflation (%)',
                            data: topInflation.map(d => d.valeur),
                            backgroundColor: '#e74c3c'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }},
                        scales: {
                            y: { beginAtZero: true }
                        }
                    }
                });

                let purchasingPower = [100];
                for (let i = 1; i < inflation.valeurs.length; i++) {
                    const prevPower = purchasingPower[i-1];
                    const inflationRate = inflation.valeurs[i] / 100;
                    purchasingPower.push(prevPower / (1 + inflationRate));
                }

                createChart('powerChart', {
                    type: 'line',
                    data: {
                        labels: inflation.annees,
                        datasets: [{
                            label: 'Valeur réelle de 100 DA (base 2004)',
                            data: purchasingPower,
                            borderColor: '#e74c3c',
                            backgroundColor: 'rgba(231, 76, 60, 0.1)',
                            borderWidth: 3,
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: (context) => {
                                        const year = context.label;
                                        const value = context.parsed.y.toFixed(2);
                                        const loss = (100 - value).toFixed(2);
                                        return `${year}: ${value} DA (perte: ${loss} DA)`;
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                title: { display: true, text: 'Valeur (DA)' }
                            }
                        }
                    }
                });
            }, 100);
        }

        // ===== PAGE 4: PÉTROLE (AVEC CAMEMBERT DÉPENDANCE) =====
        function renderPetrole() {
            const { opec } = currentData;
            const stats = calculateStats(opec.valeurs);

            document.getElementById('content').innerHTML = `
                <div class="info-box">
                    <h2> Question 4: Quelle est l'évolution du prix du pétrole en Algérie?</h2>
                    <p>Le prix du pétrole est crucial pour l'économie algérienne. Les recettes pétrolières constituent 
                    la principale source de revenus de l'État et influencent directement le budget national.</p>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <h3> Prix Moyen</h3>
                        <div class="value">$${stats.moyenne.toFixed(2)}</div>
                        <div class="subtitle">Sur ${opec.annees.length} années</div>
                    </div>
                    <div class="stat-card">
                        <h3> Maximum</h3>
                        <div class="value">$${stats.max.toFixed(2)}</div>
                        <div class="subtitle">Plus haut historique</div>
                    </div>
                    <div class="stat-card">
                        <h3> Minimum</h3>
                        <div class="value">$${stats.min.toFixed(2)}</div>
                        <div class="subtitle">Plus bas historique</div>
                    </div>
                    <div class="stat-card">
                        <h3> Prix Actuel</h3>
                        <div class="value">$${stats.last.toFixed(2)}</div>
                        <div class="subtitle">${opec.annees[opec.annees.length-1]}</div>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> Évolution du Prix du Pétrole (OPEC Basket)</h2>
                    <p>Prix moyen annuel du panier OPEC de ${opec.annees[0]} à ${opec.annees[opec.annees.length-1]}</p>
                    <div class="chart-container">
                        <canvas id="opecChart"></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> Comparaison par Période</h2>
                    <p>Prix moyen du pétrole par période économique</p>
                    <div class="chart-container">
                        <canvas id="opecBarChart"></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> Dépendance Économique aux Hydrocarbures</h2>
                    <p>Part des revenus pétroliers dans le budget de l'État algérien (estimation)</p>
                    <div class="chart-container">
                        <canvas id="dependenceChart"></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> Variations Annuelles du Prix</h2>
                    <p>Amplitude des fluctuations d'une année à l'autre (volatilité)</p>
                    <div class="chart-container">
                        <canvas id="variationChart"></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> Chutes et Hausses Majeures</h2>
                    <p>Les 5 plus grandes variations (positives et négatives)</p>
                    <div class="chart-container">
                        <canvas id="majorChangesChart"></canvas>
                    </div>
                </div>
            `;

            setTimeout(() => {
                createChart('opecChart', {
                    type: 'line',
                    data: {
                        labels: opec.annees,
                        datasets: [{
                            label: 'Prix OPEC ($/baril)',
                            data: opec.valeurs,
                            borderColor: '#43e97b',
                            backgroundColor: 'rgba(67, 233, 123, 0.1)',
                            borderWidth: 3,
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { 
                            y: { ticks: { callback: (value) => '$' + value.toFixed(0) }}
                        }
                    }
                });

                const periods = { '2003-2009': [], '2010-2014': [], '2015-2019': [], '2020-2025': [] };
                opec.annees.forEach((annee, idx) => {
                    const year = parseInt(annee);
                    if (year <= 2009) periods['2003-2009'].push(opec.valeurs[idx]);
                    else if (year <= 2014) periods['2010-2014'].push(opec.valeurs[idx]);
                    else if (year <= 2019) periods['2015-2019'].push(opec.valeurs[idx]);
                    else periods['2020-2025'].push(opec.valeurs[idx]);
                });

                const avgPeriods = Object.keys(periods).map(p => 
                    periods[p].length > 0 ? periods[p].reduce((a,b) => a+b, 0) / periods[p].length : 0
                );

                createChart('opecBarChart', {
                    type: 'bar',
                    data: {
                        labels: Object.keys(periods),
                        datasets: [{
                            label: 'Prix moyen ($/baril)',
                            data: avgPeriods,
                            backgroundColor: ['#43e97b', '#51cf66', '#94d82d', '#ffd93d']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }},
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: { callback: (value) => '$' + value.toFixed(0) }
                            }
                        }
                    }
                });

                // NOUVEAU : Camembert dépendance
                createChart('dependenceChart', {
                    type: 'pie',
                    data: {
                        labels: ['Revenus Hydrocarbures', 'Autres Revenus'],
                        datasets: [{
                            data: [47, 53],
                            backgroundColor: ['#ff6b6b', '#43e97b']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { 
                                position: 'bottom',
                                labels: {
                                    font: { size: 14 },
                                    padding: 20
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: (context) => {
                                        const label = context.label || '';
                                        const value = context.parsed || 0;
                                        return `${label}: ${value}%`;
                                    }
                                }
                            }
                        }
                    }
                });

                const variations = [];
                for (let i = 1; i < opec.valeurs.length; i++) {
                    variations.push(opec.valeurs[i] - opec.valeurs[i-1]);
                }

                createChart('variationChart', {
                    type: 'bar',
                    data: {
                        labels: opec.annees.slice(1),
                        datasets: [{
                            label: 'Variation ($/baril)',
                            data: variations,
                            backgroundColor: variations.map(v => v >= 0 ? '#27ae60' : '#e74c3c')
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }},
                        scales: {
                            y: {
                                ticks: { callback: (value) => (value >= 0 ? '+' : '') + '$' + value.toFixed(0) }
                            }
                        }
                    }
                });

                const changes = opec.annees.slice(1).map((annee, idx) => ({
                    annee: annee,
                    change: opec.valeurs[idx + 1] - opec.valeurs[idx]
                })).sort((a, b) => Math.abs(b.change) - Math.abs(a.change)).slice(0, 5);

                createChart('majorChangesChart', {
                    type: 'bar',
                    data: {
                        labels: changes.map(c => c.annee),
                        datasets: [{
                            label: 'Variation ($/baril)',
                            data: changes.map(c => c.change),
                            backgroundColor: changes.map(c => c.change >= 0 ? '#27ae60' : '#e74c3c')
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: (context) => {
                                        const value = context.parsed.y;
                                        return (value >= 0 ? 'Hausse: +' : 'Chute: ') + '$' + Math.abs(value).toFixed(2);
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                ticks: { callback: (value) => (value >= 0 ? '+' : '') + '$' + value.toFixed(0) }
                            }
                        }
                    }
                });
            }, 100);
        }

        // ===== PAGE 5: ANALYSE (TEXTE PLUS FONCÉ) =====
        function renderAnalyse() {
            const { pib, inflation, opec } = currentData;
            const commonYears = pib.annees.filter(y => 
                inflation.annees.includes(y) && opec.annees.includes(y)
            );

            document.getElementById('content').innerHTML = `
                <div class="info-box">
                    <h2> Question 5: Existe-t-il une corrélation entre pétrole, inflation et PIB ?</h2>
                    <p>Analyse des relations entre les indicateurs pour comprendre leur influence mutuelle sur l'économie algérienne.</p>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <h3> Années Analysées</h3>
                        <div class="value">${commonYears.length}</div>
                        <div class="subtitle">${commonYears[0]} - ${commonYears[commonYears.length-1]}</div>
                    </div>
                    <div class="stat-card">
                        <h3> Indicateurs</h3>
                        <div class="value">3</div>
                        <div class="subtitle">PIB, Inflation, Prix du pétrole</div>
                    </div>
                </div>

                <div class="chart-card">
                    <h2> Comparaison Normalisée</h2>
                    <p>Les séries sont normalisées entre 0 (minimum historique) et 100 (maximum historique) sur la période 2004-2024 pour comparer leurs dynamiques</p>
                    <div class="chart-container">
                        <canvas id="compChart"></canvas>
                    </div>
                </div>

                <div class="analysis-box">
                    <h2> Analyse des Corrélations</h2>
                    
                    <h3>1️ PIB ↔ Pétrole : corrélation positive modérée</h3>
                    <p>On observe que les hausses et baisses du PIB suivent souvent celles du pétrole, surtout :</p>
                    <ul>
                        <li>vers <strong>2010–2013</strong> (hausse conjointe),</li>
                        <li><strong>2014–2016</strong> (chute du pétrole suivie d'un ralentissement du PIB),</li>
                        <li><strong>2020</strong> (choc négatif commun),</li>
                        <li><strong>2021–2022</strong> (reprise simultanée).</li>
                    </ul>
                    <p> <strong>Cela suggère une dépendance du PIB aux revenus pétroliers.</strong></p>

                    <h3>2️ Inflation ↔ PIB : corrélation faible à inverse selon les périodes</h3>
                    <p>Certaines phases montrent :</p>
                    <ul>
                        <li>inflation en hausse quand le PIB ralentit (ex. <strong>2014–2016</strong>),</li>
                        <li>inflation basse lors de phases de croissance.</li>
                    </ul>
                    <p>Mais cette relation n'est pas stable dans le temps.</p>
                    <p> <strong>La corrélation est instable et contextuelle.</strong></p>

                    <h3>3️ Inflation ↔ Pétrole : corrélation positive avec décalage</h3>
                    <p>Les pics du pétrole sont souvent suivis par une hausse de l'inflation (ex. <strong>2011–2013</strong>, <strong>2021–2023</strong>).</p>
                    <p>L'effet n'est pas immédiat → <strong>retard temporel (lag)</strong>.</p>
                    <p> <strong>Le prix du pétrole influence les coûts et donc l'inflation.</strong></p>
                </div>

                <div style="background: white; padding: 30px; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); margin-top: 30px;">
                    <h2 style="margin-bottom: 20px; color: #2c3e50;"> Impact des Crises Économiques</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Événement</th>
                                <th>Année</th>
                                <th>PIB (%)</th>
                                <th>Inflation (%)</th>
                                <th>Pétrole ($)</th>
                            </tr>
                        </thead>
                        <tbody id="crisisTable"></tbody>
                    </table>
                </div>
            `;

            setTimeout(() => {
                const inflData = commonYears.map(y => inflation.valeurs[inflation.annees.indexOf(y)]);
                const opecData = commonYears.map(y => opec.valeurs[opec.annees.indexOf(y)]);
                const pibData = commonYears.map(y => pib.valeurs[pib.annees.indexOf(y)]);

                createChart('compChart', {
                    type: 'line',
                    data: {
                        labels: commonYears,
                        datasets: [
                            {
                                label: 'PIB (normalisé)',
                                data: normalize(pibData),
                                borderColor: '#667eea',
                                borderWidth: 3,
                                fill: false,
                                tension: 0.4
                            },
                            {
                                label: 'Inflation (normalisé)',
                                data: normalize(inflData),
                                borderColor: '#f5576c',
                                borderWidth: 3,
                                fill: false,
                                tension: 0.4
                            },
                            {
                                label: 'Pétrole (normalisé)',
                                data: normalize(opecData),
                                borderColor: '#43e97b',
                                borderWidth: 3,
                                fill: false,
                                tension: 0.4
                            }
                        ]
                    },
                    options: { 
                        responsive: true, 
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: true, position: 'top' }
                        }
                    }
                });

                const crises = [
                    { event: 'Crise Financière', year: '2008' },
                    { event: 'Chute Pétrole', year: '2014' },
                    { event: 'COVID-19', year: '2020' },
                    { event: 'Guerre Ukraine', year: '2022' }
                ];

                const tbody = document.getElementById('crisisTable');
                crises.forEach(crisis => {
                    if (commonYears.includes(crisis.year)) {
                        const p = pib.valeurs[pib.annees.indexOf(crisis.year)];
                        const i = inflation.valeurs[inflation.annees.indexOf(crisis.year)];
                        const o = opec.valeurs[opec.annees.indexOf(crisis.year)];

                        tbody.innerHTML += `
                            <tr>
                                <td><strong>${crisis.event}</strong></td>
                                <td>${crisis.year}</td>
                                <td class="${p >= 0 ? 'positive' : 'negative'}">${p.toFixed(2)}%</td>
                                <td class="positive">${i.toFixed(2)}%</td>
                                <td>$${o.toFixed(2)}</td>
                            </tr>
                        `;
                    }
                });
            }, 100);
        }

        window.addEventListener('load', async () => {
            console.log(' Initialisation...');
            
            if (typeof Chart === 'undefined') {
                document.getElementById('loading').innerHTML = ' Chart.js non chargé';
                return;
            }

            const success = await loadAllData();
            if (success) {
                loadPage('vue-ensemble');
            } else {
                document.getElementById('loading').innerHTML = 
                    ' Erreur. Vérifiez que le backend est lancé.';
            }
        });
