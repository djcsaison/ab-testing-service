class ExperimentsManager {
    constructor(apiClient) {
        this.api = apiClient;
        this.experimentsTable = document.getElementById('experiments-table-body');
        this.statusFilter = document.getElementById('status-filter');
        this.searchInput = document.getElementById('search-input');
        this.createBtn = document.getElementById('create-experiment-btn');
        this.detailModal = new bootstrap.Modal(document.getElementById('experiment-detail-modal'));
        this.formModal = new bootstrap.Modal(document.getElementById('experiment-form-modal'));

        // Form elements
        this.experimentForm = document.getElementById('experiment-form');
        this.formMode = document.getElementById('form-mode');
        this.experimentName = document.getElementById('experiment-name');
        this.experimentDescription = document.getElementById('experiment-description');
        this.experimentPopulation = document.getElementById('experiment-population');
        this.variantsContainer = document.getElementById('variants-container');
        this.addVariantBtn = document.getElementById('add-variant-btn');
        this.saveExperimentBtn = document.getElementById('save-experiment-btn');

        // New statistical parameter fields
        this.baseRate = document.getElementById('base-rate');
        this.minDetectableEffect = document.getElementById('min-detectable-effect');
        this.minSampleSize = document.getElementById('min-sample-size');
        this.confidenceLevel = document.getElementById('confidence-level');
        this.additionalFeatures = document.getElementById('additional-features');

        this.init();
    }

    /**
     * Initialize the experiments manager
     */
    init() {
        // Load initial experiments
        this.loadExperiments();

        // Set up event listeners
        this.statusFilter.addEventListener('change', () => this.loadExperiments());
        this.searchInput.addEventListener('input', () => this.filterExperiments());
        this.createBtn.addEventListener('click', () => this.showCreateForm());
        this.addVariantBtn.addEventListener('click', () => this.addVariantField());
        this.saveExperimentBtn.addEventListener('click', () => this.saveExperiment());

        // Add initial variant fields
        this.resetForm();

        // Set up sample size calculator
        if (this.baseRate && this.minDetectableEffect) {
            this.baseRate.addEventListener('change', () => this.updateRecommendedSampleSize());
            this.minDetectableEffect.addEventListener('change', () => this.updateRecommendedSampleSize());
            this.confidenceLevel.addEventListener('change', () => this.updateRecommendedSampleSize());
        }
    }

    /**
     * Calculate and update the recommended sample size based on statistical parameters
     */
    updateRecommendedSampleSize() {
        const baseRate = parseFloat(this.baseRate.value);
        const mde = parseFloat(this.minDetectableEffect.value);
        const confidence = parseFloat(this.confidenceLevel.value);

        if (!isNaN(baseRate) && !isNaN(mde) && mde > 0) {
            // Simple sample size calculation
            // For a proper implementation, you'd use a more accurate statistical formula
            const z = confidence === 0.99 ? 2.576 :
                confidence === 0.95 ? 1.96 :
                    confidence === 0.9 ? 1.645 : 1.96;

            const p = baseRate;
            const d = mde;

            // Sample size formula for comparing two proportions
            const sampleSize = Math.ceil(2 * p * (1 - p) * (z / d) ** 2);

            // Update the sample size field
            if (this.minSampleSize && sampleSize > 0) {
                this.minSampleSize.placeholder = `Recommended: ~${sampleSize}`;
            }
        }
    }

    /**
     * Load experiments from API with optional filtering
     */
    async loadExperiments() {
        try {
            this.showLoading();
            const status = this.statusFilter.value || null;
            const experiments = await this.api.getExperiments(status);
            this.renderExperiments(experiments);
        } catch (error) {
            this.showError('Failed to load experiments', error);
        }
    }

    /**
     * Filter experiments based on search input
     */
    filterExperiments() {
        const searchTerm = this.searchInput.value.toLowerCase();
        const rows = this.experimentsTable.querySelectorAll('tr');

        rows.forEach(row => {
            const name = row.querySelector('[data-experiment-name]').textContent.toLowerCase();
            const description = row.getAttribute('data-description')?.toLowerCase() || '';

            if (name.includes(searchTerm) || description.includes(searchTerm)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    /**
     * Render experiments to the table
     * @param {Array} experiments - List of experiments 
     */
    renderExperiments(experiments) {
        this.experimentsTable.innerHTML = '';

        if (!experiments || experiments.length === 0) {
            this.experimentsTable.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4">
                        <p class="mb-0">No experiments found</p>
                        <button class="btn btn-sm btn-outline-primary mt-2" id="empty-create-btn">
                            Create your first experiment
                        </button>
                    </td>
                </tr>
            `;

            // Add event listener to the create button
            document.getElementById('empty-create-btn')?.addEventListener('click', () => this.showCreateForm());
            return;
        }

        experiments.forEach(experiment => {
            const variantsCount = experiment.variants.length;
            const createdDate = new Date(experiment.created_at).toLocaleDateString();

            // Create table row
            const row = document.createElement('tr');
            row.setAttribute('data-experiment-id', experiment.experiment_id);
            row.setAttribute('data-description', experiment.description || '');

            row.innerHTML = `
                <td data-experiment-name>${experiment.name}</td>
                <td>
                    <span class="status-label status-${experiment.status}">
                        ${experiment.status}
                    </span>
                </td>
                <td>${variantsCount}</td>
                <td>${createdDate}</td>
                <td>${experiment.total_population || 'Unlimited'}</td>
                <td class="experiment-actions">
                    <button class="btn btn-sm btn-outline-info view-btn" title="View Details">
                        <i class="bi bi-eye"></i> View
                    </button>
                    <button class="btn btn-sm btn-outline-primary edit-btn" title="Edit">
                        <i class="bi bi-pencil"></i> Edit
                    </button>
                    <div class="dropdown d-inline-block">
                        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" 
                                type="button" data-bs-toggle="dropdown">
                            Status
                        </button>
                        <ul class="dropdown-menu">
                            ${this.renderStatusOptions(experiment.status)}
                        </ul>
                    </div>
                </td>
            `;

            // Add event listeners
            row.querySelector('.view-btn').addEventListener('click', () => this.showExperimentDetails(experiment.experiment_id));
            row.querySelector('.edit-btn').addEventListener('click', () => this.showEditForm(experiment.experiment_id));

            // Add status change listeners
            row.querySelectorAll('.status-option').forEach(option => {
                option.addEventListener('click', (e) => {
                    const newStatus = e.target.getAttribute('data-status');
                    this.updateExperimentStatus(experiment.experiment_id, newStatus);
                });
            });

            this.experimentsTable.appendChild(row);
        });
    }

    /**
     * Render status options dropdown items
     * @param {string} currentStatus - Current experiment status
     * @returns {string} HTML for dropdown items
     */
    renderStatusOptions(currentStatus) {
        const statuses = [
            { value: 'draft', label: 'Draft' },
            { value: 'active', label: 'Activate' },
            { value: 'paused', label: 'Pause' },
            { value: 'completed', label: 'Complete' }
        ];

        return statuses
            .filter(status => status.value !== currentStatus)
            .map(status => `
                <li>
                    <a class="dropdown-item status-option" href="#" data-status="${status.value}">
                        ${status.label}
                    </a>
                </li>
            `)
            .join('');
    }

    /**
     * Show experiment details modal
     * @param {string} experimentId - Experiment ID
     */
    async showExperimentDetails(experimentId) {
        try {
            const experiment = await this.api.getExperiment(experimentId);
            const stats = await this.api.getExperimentStats(experimentId, {
                includeAnalysis: true
            });

            const detailBody = document.getElementById('experiment-detail-body');
            detailBody.innerHTML = this.renderExperimentDetail(experiment, stats);

            this.detailModal.show();
        } catch (error) {
            this.showError('Failed to load experiment details', error);
        }
    }

    renderExperimentDetail(experiment, stats) {
        console.log("Displaying experiment details:", experiment); // Debug log
        console.log("Stats data:", stats); // Debug log

        // Handle both new and old stats format
        const variantStats = stats.variants || stats.variant_stats || {};
        const createdDate = new Date(experiment.created_at).toLocaleDateString();
        const updatedDate = new Date(experiment.updated_at).toLocaleDateString();
        
        // Get metadata from stats if available
        const metadata = stats.metadata || {};
        
        // Get statistical analysis if available
        const analysis = stats.analysis || null;
        
        // Get control variant
        const controlVariantName = stats.control_variant || 
            experiment.variants.find(v => v.is_control)?.name || 
            (experiment.variants.length > 0 ? experiment.variants[0].name : null);

        // Calculate totals
        let totalAssignments = 0;
        let totalImpressions = 0;
        let totalConversions = 0;

        Object.values(variantStats).forEach(variant => {
            totalAssignments += variant.assignments || 0;
            totalImpressions += variant.impression || 0;
            totalConversions += variant.conversion || 0;
        });

        // Calculate weights total
        const totalWeight = experiment.variants.reduce((sum, variant) => sum + variant.weight, 0);

        // Function to format percentage
        const formatPercent = (value, decimals = 2) => {
            if (value === null || value === undefined) return '-';
            return (value * 100).toFixed(decimals) + '%';
        };

        // Function to generate badge HTML based on status
        const getStatusBadge = (status) => {
            if (!status) return '';
            
            const badgeClass = status === 'winning' ? 'bg-success' :
                              status === 'losing' ? 'bg-danger' :
                              'bg-secondary';
                              
            const badgeText = status === 'winning' ? 'Winning' :
                             status === 'losing' ? 'Losing' :
                             'Inconclusive';
                             
            return `<span class="badge ${badgeClass} ms-2">${badgeText}</span>`;
        };

        // Create HTML for the statistics table with analysis
        let statsTableHtml = `
        <div class="table-responsive">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Variant</th>
                        <th>Weight</th>
                        <th>Assignments</th>
                        <th>Impressions</th>
                        <th>Conversions</th>
                        <th>Conv. Rate</th>
                        ${analysis ? '<th>95% CI</th><th>Status</th>' : ''}
                    </tr>
                </thead>
                <tbody>
        `;

        experiment.variants.forEach(variant => {
            const variantName = variant.name;
            const stats = variantStats[variantName] || {};
            const assignmentCount = stats.assignments || 0;
            const impressionCount = stats.impression || 0;
            const conversionCount = stats.conversion || 0;
            
            // Basic conversion rate calculation
            const convRate = impressionCount > 0
                ? (conversionCount / impressionCount)
                : 0;
                
            const convRateFormatted = formatPercent(convRate);
            
            // Get analysis data if available
            let confidenceInterval = '';
            let statusBadge = '';
            
            if (analysis && analysis.variants && analysis.variants[variantName]) {
                const variantAnalysis = analysis.variants[variantName];
                
                // Format confidence interval
                if (variantAnalysis.confidence_interval) {
                    const [lower, upper] = variantAnalysis.confidence_interval;
                    confidenceInterval = `${formatPercent(lower)} - ${formatPercent(upper)}`;
                }
                
                // Get status badge for non-control variants
                if (variantName !== controlVariantName && analysis.comparisons) {
                    const comparison = analysis.comparisons.find(c => c.variant === variantName);
                    if (comparison) {
                        statusBadge = getStatusBadge(comparison.status);
                    }
                }
            }
            
            const isControlBadge = variant.is_control
                ? '<span class="badge bg-secondary ms-2">Control</span>'
                : '';

            statsTableHtml += `
                <tr>
                    <td>
                        <strong>${variantName}</strong>${isControlBadge}
                        ${variant.description ? `<div class="small text-muted">${variant.description}</div>` : ''}
                    </td>
                    <td>${variant.weight}</td>
                    <td>${assignmentCount}</td>
                    <td>${impressionCount}</td>
                    <td>${conversionCount}</td>
                    <td>${convRateFormatted}</td>
                    ${analysis ? `<td>${confidenceInterval}</td><td>${statusBadge}</td>` : ''}
                </tr>
            `;
        });

        statsTableHtml += `
                </tbody>
            </table>
        </div>
        `;

        // Create HTML for detailed analysis if available
        let analysisHtml = '';
        if (analysis && analysis.comparisons && analysis.comparisons.length > 0) {
            analysisHtml = `
            <div class="mt-4">
                <h5 class="mb-3">Statistical Analysis</h5>
                <div class="table-responsive">
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>Variant</th>
                                <th>vs. Control</th>
                                <th>Absolute Diff</th>
                                <th>Relative Improvement</th>
                                <th>p-value</th>
                                <th>Significant</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            analysis.comparisons.forEach(comparison => {
                const isSignificant = comparison.is_significant ? 
                    '<span class="text-success">Yes</span>' : 
                    '<span class="text-muted">No</span>';
                    
                const relImprovement = formatPercent(comparison.relative_improvement);
                const absDiff = formatPercent(comparison.absolute_difference);
                const pValue = comparison.p_value < 0.001 ? 
                    '< 0.001' : 
                    comparison.p_value.toFixed(4);
                
                analysisHtml += `
                    <tr>
                        <td><strong>${comparison.variant}</strong></td>
                        <td>${comparison.control}</td>
                        <td>${absDiff}</td>
                        <td>${relImprovement}</td>
                        <td>${pValue}</td>
                        <td>${isSignificant}</td>
                        <td>${getStatusBadge(comparison.status)}</td>
                    </tr>
                `;
            });

            analysisHtml += `
                        </tbody>
                    </table>
                </div>
            </div>
            `;
        }

        // Create HTML for sample size information
        let sampleSizeHtml = '';
        if (metadata.recommended_sample_size) {
            const progress = Math.min(100, (totalImpressions / (metadata.recommended_sample_size * 2) * 100));
            sampleSizeHtml = `
            <div class="mt-4">
                <h5 class="mb-3">Sample Size</h5>
                <div class="card bg-light">
                    <div class="card-body">
                        <div class="d-flex justify-content-between mb-2">
                            <div>Recommended sample size per variant:</div>
                            <div><strong>${metadata.recommended_sample_size.toLocaleString()}</strong></div>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <div>Current total impressions:</div>
                            <div><strong>${totalImpressions.toLocaleString()}</strong></div>
                        </div>
                        <div class="progress" style="height: 20px;">
                            <div class="progress-bar" role="progressbar" style="width: ${progress}%;" 
                                aria-valuenow="${progress}" aria-valuemin="0" aria-valuemax="100">
                                ${progress.toFixed(1)}%
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            `;
        }

        return `
        <div class="experiment-detail">
            <div class="row mb-4">
                <div class="col-md-7">
                    <h4>${experiment.name}</h4>
                    <p class="text-muted">${experiment.description || 'No description'}</p>
                </div>
                <div class="col-md-5 text-md-end">
                    <span class="status-label status-${experiment.status} me-2">
                        ${experiment.status}
                    </span>
                    <small class="text-muted">
                        Created: ${createdDate} | Updated: ${updatedDate}
                    </small>
                </div>
            </div>
            
            <!-- Statistical Parameters -->
            <div class="row mb-4">
                <div class="col-12">
                    <h5 class="mb-3">Statistical Parameters</h5>
                    <div class="card bg-light">
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-3">
                                    <div class="mb-3">
                                        <label class="fw-bold">Base Rate</label>
                                        <div>${metadata.base_rate !== undefined ? formatPercent(metadata.base_rate) : 'Not specified'}</div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="mb-3">
                                        <label class="fw-bold">Min Detectable Effect</label>
                                        <div>${metadata.min_detectable_effect !== undefined ? formatPercent(metadata.min_detectable_effect) : 'Not specified'}</div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="mb-3">
                                        <label class="fw-bold">Min Sample Size</label>
                                        <div>${metadata.min_sample_size_per_group || metadata.recommended_sample_size || 'Not specified'}</div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="mb-3">
                                        <label class="fw-bold">Confidence Level</label>
                                        <div>${metadata.confidence_level ? formatPercent(metadata.confidence_level, 0) : '95%'}</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mb-4">
                <div class="col-md-4">
                    <div class="stat-card bg-light">
                        <div class="stat-title">Assignments</div>
                        <div class="stat-value">${totalAssignments}</div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stat-card bg-light">
                        <div class="stat-title">Impressions</div>
                        <div class="stat-value">${totalImpressions}</div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stat-card bg-light">
                        <div class="stat-title">Conversions</div>
                        <div class="stat-value">${totalConversions}</div>
                    </div>
                </div>
            </div>
            
            <h5 class="mb-3">Variants</h5>
            <div class="variant-distribution mb-4">
                ${experiment.variants.map(variant => {
                    const weight = variant.weight;
                    const percentage = (weight / totalWeight) * 100;
                    const isControl = variant.is_control ? ' (Control)' : '';
                    return `
                        <div class="variant-segment ${variant.is_control ? 'bg-secondary' : 'bg-primary'}" 
                            style="width: ${percentage}%; opacity: ${0.5 + (percentage / 200)}"
                            title="${variant.name}${isControl}: ${weight} (${percentage.toFixed(1)}%)">
                        </div>
                    `;
                }).join('')}
            </div>
            
            <div class="variants-table">
                ${statsTableHtml}
            </div>
            
            ${analysisHtml}
            
            ${sampleSizeHtml}
            
            <div class="row mt-4">
                <div class="col-12">
                    <h5 class="mb-3">Population Settings</h5>
                    <p>
                        ${metadata.total_population || experiment.total_population
                            ? `Limited to ${metadata.total_population || experiment.total_population} users`
                            : 'Unlimited population (no user limit set)'}
                    </p>
                </div>
            </div>
            
            ${experiment.additional_features ? `
            <div class="row mt-4">
                <div class="col-12">
                    <h5 class="mb-3">Additional Features</h5>
                    <pre class="bg-light p-3">${JSON.stringify(experiment.additional_features, null, 2)}</pre>
                </div>
            </div>
            ` : ''}
        </div>
    `;
    }

    /**
     * Show create experiment form
     */
    showCreateForm() {
        this.resetForm();
        this.formMode.value = 'create';
        document.getElementById('experiment-form-title').textContent = 'Create Experiment';
        this.formModal.show();
    }

    /**
     * Show edit experiment form
     * @param {string} experimentId - Experiment ID
     */
    async showEditForm(experimentId) {
        try {
            const experiment = await this.api.getExperiment(experimentId);
            console.log("Retrieved experiment data:", experiment); // Debug log

            this.resetForm();
            this.formMode.value = 'edit';
            document.getElementById('experiment-form-title').textContent = 'Edit Experiment';

            // Populate form with experiment data
            this.experimentName.value = experiment.name;
            this.experimentName.readOnly = true; // Cannot change experiment name once created
            this.experimentDescription.value = experiment.description || '';
            this.experimentPopulation.value = experiment.total_population || '';

            // Populate statistical parameters
            if (this.baseRate) this.baseRate.value = experiment.base_rate || '';
            if (this.minDetectableEffect) this.minDetectableEffect.value = experiment.min_detectable_effect || '';
            if (this.minSampleSize) this.minSampleSize.value = experiment.min_sample_size_per_group || '';
            if (this.confidenceLevel && experiment.confidence_level) {
                this.confidenceLevel.value = experiment.confidence_level;
            }

            // Populate additional features
            if (this.additionalFeatures && experiment.additional_features) {
                this.additionalFeatures.value = JSON.stringify(experiment.additional_features, null, 2);
            }

            // Add variant fields
            this.variantsContainer.innerHTML = '';
            experiment.variants.forEach(variant => {
                this.addVariantField(
                    variant.name,
                    variant.description,
                    variant.weight,
                    variant.is_control || false
                );
            });

            // Store experiment ID for updates
            this.experimentForm.setAttribute('data-experiment-id', experiment.experiment_id);

            // Update recommended sample size if applicable
            this.updateRecommendedSampleSize();

            this.formModal.show();
        } catch (error) {
            this.showError('Failed to load experiment for editing', error);
        }
    }

    /**
     * Reset form to initial state
     */
    resetForm() {
        this.experimentForm.reset();
        this.experimentName.readOnly = false;
        this.variantsContainer.innerHTML = '';
        this.experimentForm.removeAttribute('data-experiment-id');

        // Add two default variant fields
        this.addVariantField('control');
        this.addVariantField('treatment');
    }

    /**
     * Add a variant field to the form
     * @param {string} name - Variant name
     * @param {string} description - Variant description
     * @param {number} weight - Variant weight
     * @param {boolean} isControl - Whether this is the control variant
     */
    addVariantField(name = '', description = '', weight = 1, isControl = false) {
        const variantId = Date.now();
        const variantElement = document.createElement('div');
        variantElement.className = 'variant-item mb-3';
        variantElement.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <label class="form-label">Name</label>
                    <input type="text" class="form-control variant-name" value="${name}" required
                        pattern="[a-zA-Z0-9_-]+" title="Only alphanumeric characters, hyphens, and underscores">
                </div>
                <div class="col-md-5">
                    <label class="form-label">Description</label>
                    <input type="text" class="form-control variant-description" value="${description}">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Weight</label>
                    <input type="number" class="form-control variant-weight" value="${weight}" min="1" required>
                </div>
                <div class="col-md-2">
                    <label class="form-label">Control</label>
                    <div class="form-check mt-2">
                        <input class="form-check-input variant-control" type="radio" name="control-variant" ${isControl ? 'checked' : ''}>
                        <label class="form-check-label">Control Group</label>
                    </div>
                </div>
            </div>
            <span class="remove-variant" title="Remove Variant">×</span>
        `;
        
        // Add remove functionality
        variantElement.querySelector('.remove-variant').addEventListener('click', () => {
            // Only remove if there are more than 2 variants
            if (this.variantsContainer.children.length > 2) {
                variantElement.remove();
            } else {
                alert('An experiment must have at least 2 variants.');
            }
        });
        
        // Add control radio button change handler
        variantElement.querySelector('.variant-control').addEventListener('change', (e) => {
            if (e.target.checked) {
                // Uncheck all other control radio buttons
                this.variantsContainer.querySelectorAll('.variant-control').forEach(radio => {
                    if (radio !== e.target) {
                        radio.checked = false;
                    }
                });
            }
        });
        
        this.variantsContainer.appendChild(variantElement);
    }

    /**
     * Save experiment (create or update)
     */
    async saveExperiment() {
        try {
            if (!this.experimentForm.checkValidity()) {
                this.experimentForm.reportValidity();
                return;
            }

            // Collect variant data
            const variants = [];
            const variantItems = this.variantsContainer.querySelectorAll('.variant-item');

            variantItems.forEach(item => {
                variants.push({
                    name: item.querySelector('.variant-name').value,
                    description: item.querySelector('.variant-description').value,
                    weight: parseInt(item.querySelector('.variant-weight').value, 10),
                    is_control: item.querySelector('.variant-control').checked
                });
            });

            // Validate variant names are unique
            const variantNames = variants.map(v => v.name);
            if (new Set(variantNames).size !== variantNames.length) {
                alert('Variant names must be unique.');
                return;
            }

            // Ensure exactly one control variant
            const controlVariants = variants.filter(v => v.is_control);
            if (controlVariants.length === 0) {
                alert('You must designate one variant as the control group.');
                return;
            } else if (controlVariants.length > 1) {
                alert('Only one variant can be designated as the control group.');
                return;
            }

            // Build experiment data
            const experimentData = {
                name: this.experimentName.value,
                description: this.experimentDescription.value,
                variants: variants,
                status: 'draft' // Default to draft for new experiments
            };

            // Add statistical parameters if provided
            if (this.baseRate && this.baseRate.value) {
                experimentData.base_rate = parseFloat(this.baseRate.value);
            }

            if (this.minDetectableEffect && this.minDetectableEffect.value) {
                experimentData.min_detectable_effect = parseFloat(this.minDetectableEffect.value);
            }

            if (this.minSampleSize && this.minSampleSize.value) {
                experimentData.min_sample_size_per_group = parseInt(this.minSampleSize.value, 10);
            }

            if (this.confidenceLevel && this.confidenceLevel.value) {
                experimentData.confidence_level = parseFloat(this.confidenceLevel.value);
            }

            // Add total population if provided
            if (this.experimentPopulation.value) {
                experimentData.total_population = parseInt(this.experimentPopulation.value, 10);
            }

            // Process additional features if provided
            if (this.additionalFeatures && this.additionalFeatures.value.trim()) {
                try {
                    experimentData.additional_features = JSON.parse(this.additionalFeatures.value);
                } catch (e) {
                    alert('Additional features must be valid JSON. Please check the format.');
                    return;
                }
            }

            console.log("Saving experiment data:", experimentData); // Debug log

            // Create or update
            if (this.formMode.value === 'create') {
                await this.api.createExperiment(experimentData);
                this.showSuccess('Experiment created successfully');
            } else {
                const experimentId = this.experimentForm.getAttribute('data-experiment-id');
                delete experimentData.name; // Cannot update name
                await this.api.updateExperiment(experimentId, experimentData);
                this.showSuccess('Experiment updated successfully');
            }

            // Close modal and reload
            this.formModal.hide();
            this.loadExperiments();
        } catch (error) {
            this.showError('Failed to save experiment', error);
        }
    }

    /**
     * Update experiment status
     * @param {string} experimentId - Experiment ID
     * @param {string} status - New status
     */
    async updateExperimentStatus(experimentId, status) {
        try {
            console.log(`Updating experiment ${experimentId} status to ${status}`);
            await this.api.updateExperimentStatus(experimentId, status);
            this.showSuccess(`Experiment status updated to ${status}`);
            this.loadExperiments();
        } catch (error) {
            console.error("Status update error:", error);
            this.showError('Failed to update experiment status', error);
        }
    }

    /**
     * Show loading state
     */
    showLoading() {
        this.experimentsTable.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5">
                    <div class="spinner-border loading-spinner" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </td>
            </tr>
        `;
    }

    /**
     * Show success toast
     * @param {string} message - Success message
     */
    showSuccess(message) {
        // You can implement a more sophisticated toast notification system
        alert(message);
    }

    /**
     * Show error toast
     * @param {string} message - Error message
     * @param {Error} error - Error object
     */
    showError(message, error) {
        console.error(message, error);
        let errorDetails = error.message;

        // Try to show more helpful error details if available
        if (error.response) {
            try {
                errorDetails = JSON.stringify(error.response);
            } catch (e) {
                errorDetails = `Status: ${error.response.status} - ${error.response.statusText}`;
            }
        }

        alert(`${message}: ${errorDetails}`);
    }
}