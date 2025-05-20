class ChatUI {
    constructor() {
        this.messagesContainer = document.getElementById('chatMessages');
        this.userInput = document.getElementById('userInput');
        this.sendButton = document.getElementById('sendButton');
        this.optionButtons = document.getElementById('optionButtons');
        this.progressBar = document.getElementById('progressBar');
        this.chatInputArea = document.getElementById('chatInputArea');
        this.startOverButton = document.getElementById('startOverButton');
        
        this.selectedOptions = [];
        this.currentInputType = 'text';
        this.report = null; // Store the current report data
        
        // Add event listener for Enter key
        this.userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSendMessage();
            }
        });
        
        // Add event listener for send button
        this.sendButton.addEventListener('click', () => {
            this.handleSendMessage();
        });
        
        // Add event listener for start over button
        if (this.startOverButton) {
            this.startOverButton.addEventListener('click', () => {
                this.handleStartOver();
            });
        }
        
        // Initialize typing indicator
        this.typingIndicator = document.createElement('div');
        this.typingIndicator.className = 'typing-indicator';
        this.typingIndicator.innerHTML = '<span></span><span></span><span></span>';
    }
    
    handleSendMessage() {
        const message = this.userInput.value.trim();
        if (message) {
            this.addMessage(message, true);
            this.userInput.value = '';
            this.onSendMessage(message);
        }
    }
    
    handleStartOver() {
        // Confirm before starting over
        if (confirm("Are you sure you want to start a new assessment? Your current progress will be lost.")) {
            this.clearChat();
            this.onStartOver();
        }
    }
    
    clearChat() {
        // Clear the messages container
        this.messagesContainer.innerHTML = '';
        
        // Clear option buttons
        this.optionButtons.innerHTML = '';
        
        // Reset progress bar
        this.updateProgress(0);
        
        // Reset report data
        this.report = null;
    }
    
    showTypingIndicator() {
        // Remove any existing indicator first
        this.hideTypingIndicator();
        
        // Create and position the typing indicator
        this.typingIndicator = document.createElement('div');
        this.typingIndicator.className = 'typing-indicator';
        this.typingIndicator.innerHTML = '<span></span><span></span><span></span>';
        
        this.messagesContainer.appendChild(this.typingIndicator);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    hideTypingIndicator() {
        if (this.typingIndicator.parentNode) {
            this.messagesContainer.removeChild(this.typingIndicator);
        }
    }
    
    // Improved loading indicator that appears immediately
    showLoadingIndicator(message = 'Analyzing your symptoms...') {
        this.hideLoadingIndicator();
        
        const loadingIndicator = document.createElement('div');
        loadingIndicator.id = 'loadingIndicator';
        loadingIndicator.className = 'loading-indicator';
        
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';
        
        const text = document.createElement('p');
        text.textContent = message;
        
        loadingIndicator.appendChild(spinner);
        loadingIndicator.appendChild(text);
        
        // Append to chat container
        document.querySelector('.chat-container').appendChild(loadingIndicator);
        
        // Force reflow to ensure immediate display
        loadingIndicator.getBoundingClientRect();
        
        // Make visible with animation
        loadingIndicator.style.display = 'flex';
        loadingIndicator.style.opacity = '1';
        
        return loadingIndicator;
    }
    
    hideLoadingIndicator() {
        const indicator = document.getElementById('loadingIndicator');
        if (indicator) {
            indicator.style.display = 'none';
            if (indicator.parentNode) {
                indicator.parentNode.removeChild(indicator);
            }
        }
    }

    addMessage(message, isUser = false) {
        // Hide typing indicator if showing
        this.hideTypingIndicator();
        
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'bot-message');
        
        // Add timestamp to message
        const timestamp = document.createElement('div');
        timestamp.classList.add('message-timestamp');
        const now = new Date();
        timestamp.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Handle plain text messages
        if (typeof message === 'string') {
            messageDiv.textContent = message;
            messageDiv.appendChild(timestamp);
        } 
        // Handle report object with enhanced display
        else if (message.report) {
            messageDiv.textContent = message.message;
            messageDiv.appendChild(timestamp);
            
            // Store report data for reference in other methods
            this.report = message.report;
            
            // Use performance marking to measure report generation time
            performance.mark("reportStart");
            
            // Show loading indicator immediately
            const loadingIndicator = this.showLoadingIndicator('Preparing your health assessment...');
            
            // Reduced artificial delay - just enough for visual feedback
            setTimeout(() => {
                this.hideLoadingIndicator();
                performance.mark("reportEnd");
                performance.measure("Report Generation", "reportStart", "reportEnd");
                
                const reportContainer = document.createElement('div');
                reportContainer.classList.add('report-container');
                
                // Add report date and ID if available
                if (message.report.report_date || message.report.report_id) {
                    const reportMeta = document.createElement('div');
                    reportMeta.classList.add('report-meta');
                    
                    if (message.report.report_date) {
                        const dateSpan = document.createElement('span');
                        dateSpan.textContent = `Generated on: ${message.report.report_date}`;
                        reportMeta.appendChild(dateSpan);
                    }
                    
                    if (message.report.report_id) {
                        const idSpan = document.createElement('span');
                        idSpan.textContent = `Report ID: ${message.report.report_id}`;
                        reportMeta.appendChild(idSpan);
                    }
                    
                    reportContainer.appendChild(reportMeta);
                }
                
                // Add a header to the report
                const reportHeader = document.createElement('div');
                reportHeader.classList.add('report-header');
                reportHeader.innerHTML = '<h2>Assessment Report</h2><p>Based on the information you provided</p>';
                reportContainer.appendChild(reportHeader);
                
                // Add summary section
                if (message.report.summary) {
                    const summarySection = this.createReportSection('Summary', message.report.summary);
                    reportContainer.appendChild(summarySection);
                }
                
                // Add symptom analysis section if available
                if (message.report.symptom_analysis && message.report.symptom_analysis.length > 0) {
                    const symptomAnalysisSection = this.createSymptomAnalysisSection(
                        'Symptom Analysis', 
                        message.report.symptom_analysis
                    );
                    reportContainer.appendChild(symptomAnalysisSection);
                }
                
                // Enhanced possible conditions section (differential diagnosis)
                if (message.report.possible_conditions && message.report.possible_conditions.length > 0) {
                    const conditionsSection = this.createEnhancedDiagnosisSection(
                        'Possible Conditions', 
                        message.report.possible_conditions, 
                        message.report.condition_details
                    );
                    reportContainer.appendChild(conditionsSection);
                }
                
                // Add next steps section
                if (message.report.next_steps) {
                    const nextStepsSection = this.createReportSection('Recommended Next Steps', message.report.next_steps);
                    reportContainer.appendChild(nextStepsSection);
                }
                
                // Add warning signs section
                if (message.report.warning_signs && message.report.warning_signs.length > 0) {
                    const warningSection = this.createReportSection('Warning Signs', null, message.report.warning_signs);
                    reportContainer.appendChild(warningSection);
                }
                
                // Add self-care section
                if (message.report.self_care && message.report.self_care.length > 0) {
                    const selfCareSection = this.createReportSection('Self-Care Recommendations', null, message.report.self_care);
                    reportContainer.appendChild(selfCareSection);
                }
                
                // Add prevention section if available
                if (message.report.prevention && message.report.prevention.length > 0) {
                    const preventionSection = this.createReportSection('Prevention Measures', null, message.report.prevention);
                    reportContainer.appendChild(preventionSection);
                }
                
                // Add specialist recommendations if available
                if (message.report.specialists && message.report.specialists.length > 0) {
                    const specialistsSection = this.createSpecialistsSection('Recommended Specialists', message.report.specialists);
                    reportContainer.appendChild(specialistsSection);
                }
                
                // Add consultation options
                const consultSection = document.createElement('div');
                consultSection.classList.add('report-section', 'consult-section');
                
                const consultHeading = document.createElement('h3');
                consultHeading.textContent = 'Consultation Options';
                consultSection.appendChild(consultHeading);
                
                const consultOptions = document.createElement('div');
                consultOptions.classList.add('consult-options');
                
                // Add telemedicine option
                const telemed = document.createElement('div');
                telemed.classList.add('consult-option');
                telemed.innerHTML = `
                    <div class="consult-icon">📱</div>
                    <h4>Telemedicine</h4>
                    <p>Speak with a doctor online within minutes</p>
                    <button class="consult-button">Book Now</button>
                `;
                
                // Add in-person option
                const inPerson = document.createElement('div');
                inPerson.classList.add('consult-option');
                inPerson.innerHTML = `
                    <div class="consult-icon">🏥</div>
                    <h4>In-Person Visit</h4>
                    <p>Find doctors near you accepting appointments</p>
                    <button class="consult-button">Find Doctors</button>
                `;
                
                consultOptions.appendChild(telemed);
                consultOptions.appendChild(inPerson);
                consultSection.appendChild(consultOptions);
                reportContainer.appendChild(consultSection);
                
                // Add export/share options
                const actionButtons = document.createElement('div');
                actionButtons.classList.add('report-actions');
                
                const saveButton = document.createElement('button');
                saveButton.classList.add('report-action-button');
                saveButton.innerHTML = '<i class="fas fa-download"></i> Save as PDF';
                
                const shareButton = document.createElement('button');
                shareButton.classList.add('report-action-button');
                shareButton.innerHTML = '<i class="fas fa-share"></i> Share with Doctor';
                
                // Add start new assessment button
                const startNewButton = document.createElement('button');
                startNewButton.classList.add('report-action-button', 'start-new-button');
                startNewButton.innerHTML = '<i class="fas fa-redo-alt"></i> Start New Assessment';
                startNewButton.addEventListener('click', () => {
                    this.handleStartOver();
                });
                
                actionButtons.appendChild(saveButton);
                actionButtons.appendChild(shareButton);
                actionButtons.appendChild(startNewButton);
                reportContainer.appendChild(actionButtons);
                
                this.messagesContainer.appendChild(reportContainer);
                
                // Add animation class immediately for entrance effect
                requestAnimationFrame(() => {
                    reportContainer.classList.add('report-visible');
                });
                
                // Ensure scroll to bottom
                this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
            }, 500); // Reduced from 1500ms to 500ms for better responsiveness
            
            return;
        }
        // Handle message with info button
        else if (message.info_button) {
            messageDiv.textContent = message.text;
            
            const infoButton = document.createElement('span');
            infoButton.classList.add('info-button');
            infoButton.textContent = '?';
            infoButton.title = message.info_button.title;
            messageDiv.appendChild(infoButton);
            
            const infoContent = document.createElement('div');
            infoContent.classList.add('info-content');
            infoContent.textContent = message.info_button.content;
            messageDiv.appendChild(infoContent);
            
            infoButton.addEventListener('click', () => {
                infoContent.style.display = infoContent.style.display === 'block' ? 'none' : 'block';
            });
            
            messageDiv.appendChild(timestamp);
        }
        
        // Add animation class for entrance effect
        messageDiv.classList.add('message-entering');
        this.messagesContainer.appendChild(messageDiv);
        
        // Remove animation class after animation completes
        setTimeout(() => {
            messageDiv.classList.remove('message-entering');
        }, 300);
        
        // Ensure scroll to bottom with a slight delay to account for rendering
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }

    createReportSection(title, content, listItems = null, detailsMap = null) {
        const section = document.createElement('div');
        section.classList.add('report-section');
        
        const heading = document.createElement('h3');
        heading.textContent = title;
        section.appendChild(heading);
        
        if (content) {
            // Split content into paragraphs for better readability
            const paragraphs = content.split('. ');
            let currentParagraph = '';
            
            paragraphs.forEach((sentence, index) => {
                if (!sentence.endsWith('.') && index < paragraphs.length - 1) {
                    sentence += '.';
                }
                
                currentParagraph += sentence + ' ';
                
                // Create a new paragraph every 2-3 sentences for readability
                if ((index + 1) % 3 === 0 || index === paragraphs.length - 1) {
                    const paragraph = document.createElement('p');
                    paragraph.textContent = currentParagraph.trim();
                    section.appendChild(paragraph);
                    currentParagraph = '';
                }
            });
        }
        
        if (listItems && listItems.length > 0) {
            const list = document.createElement('ul');
            list.classList.add('report-list');
            
            listItems.forEach((item, index) => {
                const listItem = document.createElement('li');
                
                // For possible conditions, add likelihood indicators for the first 3 items
                if (title === 'Possible Conditions' && index < 3) {
                    const likelihoodIndicator = document.createElement('span');
                    likelihoodIndicator.classList.add('likelihood-indicator');
                    
                    if (index === 0) {
                        likelihoodIndicator.classList.add('high');
                        likelihoodIndicator.textContent = 'Best match';
                    } else if (index === 1) {
                        likelihoodIndicator.classList.add('medium');
                        likelihoodIndicator.textContent = 'Possible';
                    } else {
                        likelihoodIndicator.classList.add('low');
                        likelihoodIndicator.textContent = 'Less likely';
                    }
                    
                    listItem.appendChild(likelihoodIndicator);
                }
                
                // For warning signs, add an alert icon
                if (title === 'Warning Signs') {
                    const alertIcon = document.createElement('span');
                    alertIcon.classList.add('alert-icon');
                    alertIcon.innerHTML = '⚠️';
                    listItem.appendChild(alertIcon);
                }
                
                const itemText = document.createElement('span');
                itemText.textContent = item;
                listItem.appendChild(itemText);
                
                // Add expandable details for conditions if available
                if (title === 'Possible Conditions' && detailsMap && detailsMap[item]) {
                    const expandButton = document.createElement('button');
                    expandButton.classList.add('expand-button');
                    expandButton.textContent = 'More info';
                    listItem.appendChild(expandButton);
                    
                    const detailsContent = document.createElement('div');
                    detailsContent.classList.add('condition-details');
                    detailsContent.textContent = detailsMap[item];
                    detailsContent.style.display = 'none';
                    
                    expandButton.addEventListener('click', () => {
                        if (detailsContent.style.display === 'none') {
                            detailsContent.style.display = 'block';
                            expandButton.textContent = 'Less info';
                        } else {
                            detailsContent.style.display = 'none';
                            expandButton.textContent = 'More info';
                        }
                    });
                    
                    listItem.appendChild(detailsContent);
                }
                
                list.appendChild(listItem);
            });
            
            section.appendChild(list);
        }
        
        return section;
    }

    // New method for displaying symptom analysis
    createSymptomAnalysisSection(title, symptomAnalysis) {
        const section = document.createElement('div');
        section.classList.add('report-section', 'symptom-analysis-section');
        
        const heading = document.createElement('h3');
        heading.textContent = title;
        section.appendChild(heading);
        
        if (symptomAnalysis && symptomAnalysis.length > 0) {
            const symptomsContainer = document.createElement('div');
            symptomsContainer.classList.add('symptoms-container');
            
            symptomAnalysis.forEach(symptom => {
                const symptomCard = document.createElement('div');
                symptomCard.classList.add('symptom-card');
                
                // Extract symptom name and details
                const parts = symptom.split(':');
                if (parts.length > 1) {
                    const symptomName = parts[0].trim();
                    const symptomDetails = parts[1].trim();
                    
                    const nameEl = document.createElement('h4');
                    nameEl.textContent = symptomName;
                    symptomCard.appendChild(nameEl);
                    
                    const detailsEl = document.createElement('p');
                    detailsEl.textContent = symptomDetails;
                    symptomCard.appendChild(detailsEl);
                } else {
                    // If no colon separator, just display the whole text
                    const textEl = document.createElement('p');
                    textEl.textContent = symptom;
                    symptomCard.appendChild(textEl);
                }
                
                symptomsContainer.appendChild(symptomCard);
            });
            
            section.appendChild(symptomsContainer);
        }
        
        return section;
    }

    // Enhanced version of the diagnosis section to match Ada's format
    createEnhancedDiagnosisSection(title, conditions, detailsMap) {
        const section = document.createElement('div');
        section.classList.add('report-section', 'diagnosis-section');
        
        const heading = document.createElement('h3');
        heading.textContent = title;
        section.appendChild(heading);
        
        // Add explanation text
        const explanationText = document.createElement('p');
        explanationText.classList.add('diagnosis-explanation');
        explanationText.textContent = 'These conditions are listed in order of likelihood based on your reported symptoms and information. This is not a diagnosis.';
        section.appendChild(explanationText);
        
        if (conditions && conditions.length > 0) {
            const list = document.createElement('div');
            list.classList.add('diagnosis-list');
            
            conditions.forEach((condition, index) => {
                const conditionCard = document.createElement('div');
                conditionCard.classList.add('condition-card');
                
                // Add urgency indicator if available
                if (this.report && this.report.urgency_levels && this.report.urgency_levels[condition]) {
                    const urgencyIndicator = document.createElement('div');
                    urgencyIndicator.classList.add('urgency-indicator');
                    
                    const urgencyLevel = this.report.urgency_levels[condition];
                    if (urgencyLevel.includes('immediate')) {
                        urgencyIndicator.classList.add('urgent');
                        urgencyIndicator.textContent = 'Needs urgent attention';
                    } else if (urgencyLevel.includes('prompt')) {
                        urgencyIndicator.classList.add('semi-urgent');
                        urgencyIndicator.textContent = 'Needs prompt attention';
                    } else if (urgencyLevel.includes('routine')) {
                        urgencyIndicator.classList.add('routine');
                        urgencyIndicator.textContent = 'Routine care recommended';
                    } else {
                        urgencyIndicator.classList.add('self-care');
                        urgencyIndicator.textContent = 'Self-care appropriate';
                    }
                    
                    conditionCard.appendChild(urgencyIndicator);
                }
                
                // Add condition name with likelihood percentage
                const conditionHeader = document.createElement('div');
                conditionHeader.classList.add('condition-header');
                
                const conditionName = document.createElement('h4');
                conditionName.textContent = condition;
                conditionHeader.appendChild(conditionName);
                
                // Add likelihood percentage if available
                if (this.report && this.report.likelihood_percentages && this.report.likelihood_percentages[condition]) {
                    const likelihoodPercentage = document.createElement('span');
                    likelihoodPercentage.classList.add('likelihood-percentage');
                    likelihoodPercentage.textContent = `${this.report.likelihood_percentages[condition]}%`;
                    conditionHeader.appendChild(likelihoodPercentage);
                }
                
                conditionCard.appendChild(conditionHeader);
                
                // Add condition description if available
                if (detailsMap && detailsMap[condition]) {
                    const conditionDesc = document.createElement('p');
                    conditionDesc.classList.add('condition-description');
                    conditionDesc.textContent = detailsMap[condition];
                    conditionCard.appendChild(conditionDesc);
                }
                
                // Add supporting symptoms if available
                if (this.report && this.report.supporting_symptoms && this.report.supporting_symptoms[condition]) {
                    const supportingSymptoms = this.report.supporting_symptoms[condition];
                    if (supportingSymptoms.length > 0) {
                        const symptomsHeading = document.createElement('h5');
                        symptomsHeading.textContent = 'Key symptoms:';
                        conditionCard.appendChild(symptomsHeading);
                        
                        const symptomsList = document.createElement('ul');
                        symptomsList.classList.add('supporting-symptoms');
                        
                        supportingSymptoms.forEach(symptom => {
                            const symptomItem = document.createElement('li');
                            symptomItem.textContent = symptom;
                            symptomsList.appendChild(symptomItem);
                        });
                        
                        conditionCard.appendChild(symptomsList);
                    }
                }
                
                // Add action buttons
                const actionContainer = document.createElement('div');
                actionContainer.classList.add('condition-actions');
                
                // Add seek advice button
                const seekAdviceBtn = document.createElement('button');
                seekAdviceBtn.classList.add('seek-advice-btn');
                seekAdviceBtn.textContent = 'Seek medical advice';
                seekAdviceBtn.addEventListener('click', () => {
                    // Scroll to consultation options
                    document.querySelector('.consult-section').scrollIntoView({ behavior: 'smooth' });
                });
                
                // Add learn more button
                const learnMoreBtn = document.createElement('button');
                learnMoreBtn.classList.add('learn-more-btn');
                learnMoreBtn.textContent = 'Learn more';
                learnMoreBtn.addEventListener('click', () => {
                    window.open(`https://www.mayoclinic.org/search/search-results?q=${encodeURIComponent(condition)}`, '_blank');
                });
                
                actionContainer.appendChild(seekAdviceBtn);
                actionContainer.appendChild(learnMoreBtn);
                conditionCard.appendChild(actionContainer);
                
                list.appendChild(conditionCard);
            });
            
            section.appendChild(list);
        }
        
        return section;
    }

    createSpecialistsSection(title, specialists) {
        const section = document.createElement('div');
        section.classList.add('report-section', 'specialists-section');
        
        const heading = document.createElement('h3');
        heading.textContent = title;
        section.appendChild(heading);
        
        const specialistsList = document.createElement('div');
        specialistsList.classList.add('specialists-list');
        
        specialists.forEach(specialist => {
            const specialistItem = document.createElement('div');
            specialistItem.classList.add('specialist-item');
            
            // Add relevance indicator if available
            if (specialist.relevance_score) {
                const relevanceIndicator = document.createElement('div');
                relevanceIndicator.classList.add('relevance-indicator');
                
                const relevanceBar = document.createElement('div');
                relevanceBar.classList.add('relevance-bar');
                relevanceBar.style.width = `${Math.min(specialist.relevance_score * 20, 100)}%`;
                
                relevanceIndicator.appendChild(relevanceBar);
                specialistItem.appendChild(relevanceIndicator);
            }
            
            const nameEl = document.createElement('h4');
            nameEl.textContent = specialist.name;
            
            const descEl = document.createElement('p');
            descEl.textContent = specialist.description;
            
            const findButton = document.createElement('button');
            findButton.classList.add('find-specialist-button');
            findButton.textContent = 'Find Nearby';
            
            specialistItem.appendChild(nameEl);
            specialistItem.appendChild(descEl);
            specialistItem.appendChild(findButton);
            specialistsList.appendChild(specialistItem);
        });
        
        section.appendChild(specialistsList);
        return section;
    }

    updateProgress(progress) {
        // Animate progress bar
        this.progressBar.style.transition = 'width 0.5s ease-in-out';
        this.progressBar.style.width = `${progress}%`;
        
        // Add visual cue for progress milestones
        if (progress >= 25 && progress < 50) {
            this.progressBar.className = 'progress-bar progress-low';
        } else if (progress >= 50 && progress < 75) {
            this.progressBar.className = 'progress-bar progress-medium';
        } else if (progress >= 75) {
            this.progressBar.className = 'progress-bar progress-high';
        }
    }

    showOptions(options, multipleSelect = false) {
        this.optionButtons.innerHTML = '';
        this.selectedOptions = [];
        
        // If we have more than 5 options, use a dropdown instead of buttons
        if (options.length > 5 && !multipleSelect) {
            this.showDropdownOptions(options);
            return;
        }
        
        // Add staggered animation for options
        options.forEach((option, index) => {
            const button = document.createElement('button');
            button.classList.add('option-button');
            button.textContent = option;
            button.style.animationDelay = `${index * 0.1}s`;
            
            button.addEventListener('click', () => {
                if (multipleSelect) {
                    if (this.selectedOptions.includes(option)) {
                        // Deselect option
                        this.selectedOptions = this.selectedOptions.filter(item => item !== option);
                        button.classList.remove('selected');
                    } else {
                        // Select option
                        this.selectedOptions.push(option);
                        button.classList.add('selected');
                    }
                } else {
                    // Single select - immediately return the selection
                    this.addMessage(option, true);
                    this.optionButtons.innerHTML = '';
                    this.onOptionSelected(option);
                }
            });
            
            this.optionButtons.appendChild(button);
        });
        
        if (multipleSelect) {
            // Add a "Done" button for multiple selections
            const doneButton = document.createElement('button');
            doneButton.classList.add('option-button', 'done-button');
            doneButton.textContent = 'Done';
            doneButton.style.animationDelay = `${options.length * 0.1}s`;
            
            doneButton.addEventListener('click', () => {
                const selectedText = this.selectedOptions.join(', ');
                this.addMessage(selectedText, true);
                this.optionButtons.innerHTML = '';
                this.onOptionSelected(selectedText);
            });
            
            this.optionButtons.appendChild(doneButton);
        }
        
        // Ensure options are visible by scrolling to them
        setTimeout(() => {
            this.optionButtons.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
    }

    showDropdownOptions(options) {
        const selectContainer = document.createElement('div');
        selectContainer.classList.add('select-container');
        
        // Add search filter for long lists
        if (options.length > 10) {
            const filterInput = document.createElement('input');
            filterInput.type = 'text';
            filterInput.placeholder = 'Type to filter options...';
            filterInput.classList.add('filter-input');
            
            filterInput.addEventListener('input', () => {
                const filterText = filterInput.value.toLowerCase();
                const optionElements = Array.from(select.options).slice(1); // Skip placeholder
                
                optionElements.forEach(option => {
                    const optionText = option.textContent.toLowerCase();
                    option.style.display = optionText.includes(filterText) ? '' : 'none';
                });
            });
            
            selectContainer.appendChild(filterInput);
        }
        
        const selectLabel = document.createElement('label');
        selectLabel.textContent = 'Please select an option:';
        selectLabel.setAttribute('for', 'optionSelect');
        
        const select = document.createElement('select');
        select.id = 'optionSelect';
        select.classList.add('option-select');
        
        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Select an option';
        defaultOption.disabled = true;
        defaultOption.selected = true;
        select.appendChild(defaultOption);
        
        // Add all options
        options.forEach(option => {
            const optionEl = document.createElement('option');
            optionEl.value = option;
            optionEl.textContent = option;
            select.appendChild(optionEl);
        });
        
        const submitButton = document.createElement('button');
        submitButton.textContent = 'Submit';
        submitButton.classList.add('option-button');
        submitButton.disabled = true;
        
        select.addEventListener('change', () => {
            submitButton.disabled = !select.value;
        });
        
        submitButton.addEventListener('click', () => {
            if (select.value) {
                this.addMessage(select.value, true);
                this.optionButtons.innerHTML = '';
                this.onOptionSelected(select.value);
            }
        });
        
        selectContainer.appendChild(selectLabel);
        selectContainer.appendChild(select);
        selectContainer.appendChild(submitButton);
        
        // Add animation
        selectContainer.classList.add('select-container-entering');
        this.optionButtons.appendChild(selectContainer);
        
        setTimeout(() => {
            selectContainer.classList.remove('select-container-entering');
            // Ensure the dropdown is visible
            this.optionButtons.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 300);
    }

    setInputType(inputType, placeholder = '') {
        this.currentInputType = inputType;
        
        // Reset any existing search containers
        const existingContainer = document.querySelector('.symptom-search-container');
        if (existingContainer) {
            const originalInput = this.userInput;
            if (originalInput.parentElement === existingContainer) {
                existingContainer.parentElement.insertBefore(originalInput, existingContainer);
                existingContainer.remove();
            }
        }
        
        if (inputType === 'text' || inputType === 'number') {
            this.chatInputArea.style.display = 'flex';
            this.userInput.placeholder = placeholder || `Type ${inputType} here...`;
            this.userInput.type = inputType;
        } else if (inputType === 'symptom_search') {
            this.chatInputArea.style.display = 'flex';
            this.userInput.placeholder = placeholder || 'Search for a symptom...';
            this.userInput.type = 'text';
            
            // Set up symptom search functionality
            this.setupSymptomSearch();
        } else {
            this.chatInputArea.style.display = 'none';
        }
        
        // Ensure the input is visible by scrolling to it
        setTimeout(() => {
            this.chatInputArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            this.userInput.focus();
        }, 100);
    }

    setupSymptomSearch() {
        // Create a container for search results
        const searchContainer = document.createElement('div');
        searchContainer.classList.add('symptom-search-container');
        
        // Move the input to the search container
        const originalInput = this.userInput;
        this.chatInputArea.removeChild(originalInput);
        searchContainer.appendChild(originalInput);
        
        // Set ARIA attributes for accessibility
        originalInput.setAttribute('aria-autocomplete', 'list');
        originalInput.setAttribute('role', 'combobox');
        originalInput.setAttribute('aria-expanded', 'false');
        
        const searchResultsContainer = document.createElement('div');
        searchResultsContainer.classList.add('symptom-search-results');
        searchResultsContainer.setAttribute('role', 'listbox');
        
        // Fix positioning - explicitly position above the input
        searchResultsContainer.style.position = 'absolute';
        searchResultsContainer.style.bottom = '100%';
        searchResultsContainer.style.left = '0';
        searchResultsContainer.style.right = '0';
        searchResultsContainer.style.maxHeight = '250px';
        searchResultsContainer.style.overflowY = 'auto';
        searchResultsContainer.style.zIndex = '200';
        searchResultsContainer.style.backgroundColor = 'white';
        searchResultsContainer.style.border = '1px solid #ddd';
        searchResultsContainer.style.borderRadius = '10px';
        searchResultsContainer.style.boxShadow = '0 -4px 10px rgba(0,0,0,0.1)';
        searchResultsContainer.style.marginBottom = '5px';
        
        // Generate a unique ID for ARIA relationships
        const listboxId = 'symptom-results-' + Math.random().toString(36).substr(2, 9);
        searchResultsContainer.id = listboxId;
        originalInput.setAttribute('aria-controls', listboxId);
        
        searchContainer.appendChild(searchResultsContainer);
        this.chatInputArea.insertBefore(searchContainer, this.sendButton);
        
        // Clear existing results
        searchResultsContainer.innerHTML = '';
        searchResultsContainer.style.display = 'none';
        
        // Set up input event listener for search with debugging
        const debouncedSearch = this.debounce(async (query) => {
            if (query.length < 2) {
                searchResultsContainer.innerHTML = '';
                searchResultsContainer.style.display = 'none';
                originalInput.setAttribute('aria-expanded', 'false');
                return;
            }
            
            try {
                console.log("Searching for:", query); // Debug log
                const results = await this.onSymptomSearch(query);
                console.log("Search results:", results); // Debug log
                
                // Update ARIA attributes
                originalInput.setAttribute('aria-expanded', 'true');
                
                this.updateSearchResults(results, searchResultsContainer, query);
            } catch (error) {
                console.error('Error searching symptoms:', error);
                searchResultsContainer.innerHTML = '';
                const errorMsg = document.createElement('div');
                errorMsg.classList.add('symptom-result', 'error-message');
                errorMsg.textContent = 'Error searching symptoms. Please try again.';
                searchResultsContainer.appendChild(errorMsg);
                searchResultsContainer.style.display = 'block';
            }
        }, 300);
        
        originalInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            debouncedSearch(query);
        });
        
        // Add keyboard navigation
        originalInput.addEventListener('keydown', (e) => {
            const items = searchResultsContainer.querySelectorAll('.symptom-result');
            const activeItem = searchResultsContainer.querySelector('.symptom-result.active');
            let index = -1;
            
            if (activeItem) {
                index = Array.from(items).indexOf(activeItem);
            }
            
            // Down arrow
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (searchResultsContainer.style.display === 'block') {
                    if (index < items.length - 1) {
                        if (activeItem) activeItem.classList.remove('active');
                        items[index + 1].classList.add('active');
                        items[index + 1].scrollIntoView({ block: 'nearest' });
                    }
                }
            }
            
            // Up arrow
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (searchResultsContainer.style.display === 'block') {
                    if (index > 0) {
                        if (activeItem) activeItem.classList.remove('active');
                        items[index - 1].classList.add('active');
                        items[index - 1].scrollIntoView({ block: 'nearest' });
                    }
                }
            }
            
            // Enter key
            if (e.key === 'Enter') {
                if (activeItem) {
                    e.preventDefault();
                    originalInput.value = activeItem.querySelector('.symptom-name').textContent;
                    searchResultsContainer.style.display = 'none';
                    originalInput.setAttribute('aria-expanded', 'false');
                }
            }
            
            // Escape key
            if (e.key === 'Escape') {
                searchResultsContainer.style.display = 'none';
                originalInput.setAttribute('aria-expanded', 'false');
            }
        });
        
        // Hide results when clicking outside
        document.addEventListener('click', (e) => {
            if (!searchContainer.contains(e.target)) {
                searchResultsContainer.style.display = 'none';
                originalInput.setAttribute('aria-expanded', 'false');
            }
        });
    }
    
    updateSearchResults(results, container, query) {
        container.innerHTML = '';
        
        if (results && results.length > 0) {
            results.forEach((symptom, index) => {
                const resultItem = document.createElement('div');
                resultItem.classList.add('symptom-result');
                resultItem.setAttribute('role', 'option');
                resultItem.setAttribute('id', 'symptom-option-' + index);
                
                // Highlight the matching text
                const nameSpan = document.createElement('span');
                nameSpan.classList.add('symptom-name');
                
                // Highlight the matching part of the name
                const lowerName = symptom.name.toLowerCase();
                const lowerQuery = query.toLowerCase();
                const startIndex = lowerName.indexOf(lowerQuery);
                
                if (startIndex >= 0) {
                    const beforeMatch = symptom.name.substring(0, startIndex);
                    const match = symptom.name.substring(startIndex, startIndex + query.length);
                    const afterMatch = symptom.name.substring(startIndex + query.length);
                    
                    nameSpan.innerHTML = beforeMatch + '<strong>' + match + '</strong>' + afterMatch;
                } else {
                    nameSpan.textContent = symptom.name;
                }
                
                const descSpan = document.createElement('span');
                descSpan.classList.add('symptom-description');
                descSpan.textContent = symptom.description ? 
                    (symptom.description.length > 60 ? 
                        symptom.description.substring(0, 60) + '...' : 
                        symptom.description) : 
                    '';
                
                resultItem.appendChild(nameSpan);
                resultItem.appendChild(document.createElement('br'));
                resultItem.appendChild(descSpan);
                
                resultItem.addEventListener('click', () => {
                    this.userInput.value = symptom.name;
                    container.style.display = 'none';
                    this.userInput.setAttribute('aria-expanded', 'false');
                    this.sendButton.focus();
                });
                
                // Highlight on hover
                resultItem.addEventListener('mouseenter', () => {
                    const active = container.querySelector('.symptom-result.active');
                    if (active) active.classList.remove('active');
                    resultItem.classList.add('active');
                });
                
                container.appendChild(resultItem);
            });
            container.style.display = 'block';
        } else {
            // Show "no results" message
            const noResults = document.createElement('div');
            noResults.classList.add('symptom-result', 'no-results');
            noResults.textContent = 'No matching symptoms found';
            container.appendChild(noResults);
            container.style.display = 'block';
        }
    }

    debounce(func, wait) {
        let timeout;
        return function(...args) {
            const context = this;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait);
        };
    }

    // Event handler callbacks - to be set by the controller
    onSendMessage = (message) => {};
    onOptionSelected = (option) => {};
    onSymptomSearch = (query) => {};
    onStartOver = () => {}; // New callback for start over functionality
}
