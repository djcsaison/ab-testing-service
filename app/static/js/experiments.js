/**
 * Experiments management functionality
 */
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
            const stats = await this.api.getExperimentStats(experimentId);
            
            const detailBody = document.getElementById('experiment-detail-body');
            detailBody.innerHTML = this.renderExperimentDetail(experiment, stats);
            
            this.detailModal.show();
        } catch (error) {
            this.showError('Failed to load experiment details', error);
        }
    }

    /**
     * Render experiment detail view
     * @param {Object} experiment - Experiment data
     * @param {Object} stats - Experiment statistics
     * @returns {string} HTML for detail view
     */
    renderExperimentDetail(experiment, stats) {
        const variantStats = stats.variant_stats || {};
        const createdDate = new Date(experiment.created_at).toLocaleDateString();
        const updatedDate = new Date(experiment.updated_at).toLocaleDateString();
        
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
                        return `
                            <div class="variant-segment bg-primary" 
                                style="width: ${percentage}%; opacity: ${0.5 + (percentage/200)}"
                                title="${variant.name}: ${weight} (${percentage.toFixed(1)}%)">
                            </div>
                        `;
                    }).join('')}
                </div>
                
                <div class="variants-table">
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
                                </tr>
                            </thead>
                            <tbody>
                                ${experiment.variants.map(variant => {
                                    const stats = variantStats[variant.name] || {};
                                    const assignments = stats.assignments || 0;
                                    const impressions = stats.impression || 0;
                                    const conversions = stats.conversion || 0;
                                    const convRate = impressions > 0 
                                        ? ((conversions / impressions) * 100).toFixed(2) + '%' 
                                        : '-';
                                        
                                    return `
                                        <tr>
                                            <td>
                                                <strong>${variant.name}</strong>
                                                ${variant.description ? `<div class="small text-muted">${variant.description}</div>` : ''}
                                            </td>
                                            <td>${variant.weight}</td>
                                            <td>${assignments}</td>
                                            <td>${impressions}</td>
                                            <td>${conversions}</td>
                                            <td>${convRate}</td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="row mt-4">
                    <div class="col-12">
                        <h5 class="mb-3">Population Settings</h5>
                        <p>
                            ${experiment.total_population 
                                ? `Limited to ${experiment.total_population} users` 
                                : 'Unlimited population (no user limit set)'}
                        </p>
                    </div>
                </div>
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
            
            this.resetForm();
            this.formMode.value = 'edit';
            document.getElementById('experiment-form-title').textContent = 'Edit Experiment';
            
            // Populate form with experiment data
            this.experimentName.value = experiment.name;
            this.experimentName.readOnly = true; // Cannot change experiment name once created
            this.experimentDescription.value = experiment.description || '';
            this.experimentPopulation.value = experiment.total_population || '';
            
            // Add variant fields
            this.variantsContainer.innerHTML = '';
            experiment.variants.forEach(variant => {
                this.addVariantField(variant.name, variant.description, variant.weight);
            });
            
            // Store experiment ID for updates
            this.experimentForm.setAttribute('data-experiment-id', experiment.experiment_id);
            
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
     */
    addVariantField(name = '', description = '', weight = 1) {
        const variantId = Date.now();
        const variantElement = document.createElement('div');
        variantElement.className = 'variant-item mb-3';
        variantElement.innerHTML = `
            <div class="row">
                <div class="col-md-4">
                    <label class="form-label">Name</label>
                    <input type="text" class="form-control variant-name" value="${name}" required
                           pattern="[a-zA-Z0-9_-]+" title="Only alphanumeric characters, hyphens, and underscores">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Description</label>
                    <input type="text" class="form-control variant-description" value="${description}">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Weight</label>
                    <input type="number" class="form-control variant-weight" value="${weight}" min="1" required>
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
                    weight: parseInt(item.querySelector('.variant-weight').value, 10)
                });
            });
            
            // Validate variant names are unique
            const variantNames = variants.map(v => v.name);
            if (new Set(variantNames).size !== variantNames.length) {
                alert('Variant names must be unique.');
                return;
            }
            
            // Build experiment data
            const experimentData = {
                name: this.experimentName.value,
                description: this.experimentDescription.value,
                variants: variants,
                status: 'draft' // Default to draft for new experiments
            };
            
            // Add total population if provided
            if (this.experimentPopulation.value) {
                experimentData.total_population = parseInt(this.experimentPopulation.value, 10);
            }
            
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