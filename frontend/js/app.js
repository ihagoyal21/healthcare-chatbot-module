document.addEventListener('DOMContentLoaded', () => {
    const api = new ApiService();
    const ui = new ChatUI();
    
    // Session state management
    let sessionState = {
        sessionId: null,
        currentFlow: 'main',
        conversationHistory: [],
        symptomSpecificMode: false,
        currentSymptom: null,
        questionStack: [],
        allowBacktracking: true,
        processingResponse: false, // Add a flag to prevent multiple responses being processed simultaneously
        assessmentCompleted: false // Track if assessment is completed
    };
    
    // Set up event handlers
    ui.onSendMessage = async (message) => {
        try {
            // Prevent sending another message while processing a response
            if (sessionState.processingResponse) {
                console.log('Still processing previous response, please wait...');
                return;
            }
            
            sessionState.processingResponse = true;
            ui.showTypingIndicator();
            
            const response = await api.sendMessage(message, sessionState.sessionId);
            
            // Update session ID if not already set
            if (!sessionState.sessionId && response.session_id) {
                sessionState.sessionId = response.session_id;
            }
            
            // Track conversation history
            sessionState.conversationHistory.push({
                role: 'user',
                content: message,
                timestamp: new Date().toISOString()
            });
            
            // Add a small delay to ensure the UI can catch up
            setTimeout(() => {
                handleResponse(response);
                sessionState.processingResponse = false;
            }, 100);
        } catch (error) {
            console.error('Error sending message:', error);
            ui.hideTypingIndicator();
            ui.addMessage('Sorry, there was an error processing your request. Please try again.');
            sessionState.processingResponse = false;
        }
    };
    
    ui.onOptionSelected = async (option) => {
        try {
            // Prevent selecting another option while processing a response
            if (sessionState.processingResponse) {
                console.log('Still processing previous response, please wait...');
                return;
            }
            
            sessionState.processingResponse = true;
            ui.showTypingIndicator();
            
            // Save current state for potential backtracking
            if (sessionState.allowBacktracking) {
                sessionState.questionStack.push({
                    message: ui.lastBotMessage,
                    options: ui.lastOptions,
                    inputType: ui.currentInputType
                });
            }
            
            const response = await api.sendMessage(option, sessionState.sessionId);
            
            // Track conversation history
            sessionState.conversationHistory.push({
                role: 'user',
                content: option,
                timestamp: new Date().toISOString()
            });
            
            // Add a small delay to ensure the UI can catch up
            setTimeout(() => {
                handleResponse(response);
                sessionState.processingResponse = false;
            }, 100);
        } catch (error) {
            console.error('Error processing option:', error);
            ui.hideTypingIndicator();
            ui.addMessage('Sorry, there was an error processing your selection. Please try again.');
            sessionState.processingResponse = false;
        }
    };
    
    ui.onSymptomSearch = async (query) => {
        try {
            return await api.searchSymptoms(query);
        } catch (error) {
            console.error('Error searching symptoms:', error);
            return [];
        }
    };
    
    // Handle going back in the conversation
    ui.onGoBack = async () => {
        if (sessionState.processingResponse) {
            console.log('Still processing previous response, please wait...');
            return;
        }
        
        if (sessionState.questionStack.length > 0) {
            try {
                sessionState.processingResponse = true;
                
                // Get the previous state
                const previousState = sessionState.questionStack.pop();
                
                // If in symptom-specific mode, we might need to exit that mode
                if (sessionState.symptomSpecificMode && sessionState.questionStack.length === 0) {
                    sessionState.symptomSpecificMode = false;
                    sessionState.currentSymptom = null;
                }
                
                // Restore the previous UI state
                ui.restorePreviousState(previousState);
                
                // Optionally, notify the backend about going back
                await api.goBack(sessionState.sessionId);
                
                sessionState.processingResponse = false;
            } catch (error) {
                console.error('Error going back:', error);
                ui.addMessage('Sorry, there was an error going back in the conversation. Please continue from here.');
                sessionState.processingResponse = false;
            }
        } else {
            ui.addMessage('You\'re at the beginning of the conversation.');
        }
    };
    
    // Handle starting over
    ui.onStartOver = async () => {
        try {
            if (sessionState.processingResponse) {
                console.log('Still processing previous response, please wait...');
                return;
            }
            
            sessionState.processingResponse = true;
            ui.showLoadingIndicator('Starting a new assessment...');
            
            // Clear the chat UI
            ui.clearChat();
            
            // Reset session state
            sessionState = {
                sessionId: null,
                currentFlow: 'main',
                conversationHistory: [],
                symptomSpecificMode: false,
                currentSymptom: null,
                questionStack: [],
                allowBacktracking: true,
                processingResponse: true,
                assessmentCompleted: false
            };
            
            // Start a new assessment
            const response = await api.startAssessment();
            
            // Set the session ID
            if (response.session_id) {
                sessionState.sessionId = response.session_id;
            }
            
            // Initialize conversation history
            sessionState.conversationHistory = [{
                role: 'assistant',
                content: response.message || 'Welcome to the health assessment',
                timestamp: new Date().toISOString()
            }];
            
            ui.hideLoadingIndicator();
            handleResponse(response);
            
            // Disable back button initially
            const backButton = document.getElementById('backButton');
            if (backButton) backButton.disabled = true;
            
            // Disable save button initially
            const saveButton = document.getElementById('saveButton');
            if (saveButton) saveButton.disabled = true;
            
            sessionState.processingResponse = false;
        } catch (error) {
            console.error('Error starting over:', error);
            ui.hideLoadingIndicator();
            ui.addMessage('Sorry, there was an error starting a new assessment. Please refresh the page and try again.');
            sessionState.processingResponse = false;
        }
    };
    
    // Handle saving the assessment
    ui.onSaveAssessment = async () => {
        if (!sessionState.sessionId) {
            ui.showNotification('Cannot save assessment: No active session');
            return;
        }
        
        if (sessionState.processingResponse) {
            ui.showNotification('Please wait until current processing is complete');
            return;
        }
        
        try {
            sessionState.processingResponse = true;
            const response = await api.saveAssessment(sessionState.sessionId);
            
            if (response.assessment_id) {
                ui.showNotification('Assessment saved successfully!');
                
                // Create a shareable link or download option
                const shareLink = `${window.location.origin}/assessment/${response.assessment_id}`;
                ui.showShareOptions(shareLink);
            }
            
            sessionState.processingResponse = false;
        } catch (error) {
            console.error('Error saving assessment:', error);
            ui.showNotification('Failed to save assessment. Please try again.');
            sessionState.processingResponse = false;
        }
    };
    
    // Handle user input submission
    document.getElementById('sendButton').addEventListener('click', () => {
        const message = ui.userInput.value.trim();
        if (message && !sessionState.processingResponse) {
            ui.addMessage(message, true);
            ui.userInput.value = '';
            ui.onSendMessage(message);
        }
    });
    
    ui.userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            const message = ui.userInput.value.trim();
            if (message && !sessionState.processingResponse) {
                ui.addMessage(message, true);
                ui.userInput.value = '';
                ui.onSendMessage(message);
            }
        }
    });
    
    // Add back button functionality
    const backButton = document.getElementById('backButton');
    if (backButton) {
        backButton.addEventListener('click', () => {
            if (!sessionState.processingResponse) {
                ui.onGoBack();
            }
        });
    }
    
    // Add save button functionality
    const saveButton = document.getElementById('saveButton');
    if (saveButton) {
        saveButton.addEventListener('click', () => {
            if (!sessionState.processingResponse) {
                ui.onSaveAssessment();
            }
        });
    }
    
    // Add start over button functionality
    const startOverButton = document.getElementById('startOverButton');
    if (startOverButton) {
        startOverButton.addEventListener('click', () => {
            if (!sessionState.processingResponse) {
                // Confirm before starting over
                if (confirm("Are you sure you want to start a new assessment? Your current progress will be lost.")) {
                    ui.onStartOver();
                }
            }
        });
    }
    
    // Process bot responses
    function handleResponse(response) {
        // Check if response is valid
        if (!response) {
            console.error('Received empty response from server');
            ui.hideTypingIndicator();
            ui.addMessage('Sorry, there was an error processing your request. Please try again.');
            return;
        }
        
        // Handle error responses
        if (response.error) {
            console.error('Error from server:', response.error);
            ui.hideTypingIndicator();
            ui.showNotification(`Error: ${response.error}`);
            return;
        }
        
        ui.hideTypingIndicator();
        
        // Update progress bar if progress is provided
        if (response.progress !== undefined) {
            ui.updateProgress(response.progress);
        }
        
        // Check if we're transitioning to a symptom-specific flow
        if (response.current_flow === 'symptom_specific' && !sessionState.symptomSpecificMode) {
            sessionState.symptomSpecificMode = true;
            sessionState.currentSymptom = response.current_symptom;
            
            // Enable back button when entering symptom-specific flow
            if (backButton) backButton.disabled = false;
        }
        
        // Check if we're exiting a symptom-specific flow
        if (sessionState.symptomSpecificMode && response.current_flow === 'main') {
            sessionState.symptomSpecificMode = false;
            sessionState.currentSymptom = null;
        }
        
        // Track conversation history
        sessionState.conversationHistory.push({
            role: 'assistant',
            content: response.message || '',
            timestamp: new Date().toISOString()
        });
        
        // Store the last bot message for backtracking
        ui.lastBotMessage = response.message;
        ui.lastOptions = response.options;
        
        // Display the message
        if (response.report) {
            ui.addMessage(response);
            
            // Enable save button when report is generated
            if (saveButton) saveButton.disabled = false;
            
            // Mark assessment as completed
            sessionState.assessmentCompleted = true;
            
            // Reset symptom-specific mode when report is generated
            sessionState.symptomSpecificMode = false;
            sessionState.currentSymptom = null;
            sessionState.questionStack = [];
        } else if (response.message) {
            ui.addMessage(response.message, false, response.info_button);
        }
        
        // Handle input type
        if (response.input_type) {
            ui.setInputType(response.input_type, response.placeholder);
        }
        
        // Show options if provided
        if (response.options && response.options.length > 0) {
            ui.showOptions(response.options, response.multiple_select);
        }
        
        // If we have a new state, update our tracking
        if (response.current_state) {
            sessionState.currentState = response.current_state;
        }
    }
    
    // Start the assessment
    async function startAssessment() {
        try {
            sessionState.processingResponse = true;
            ui.showLoadingIndicator('Starting health assessment...');
            
            const response = await api.startAssessment();
            
            // Set the session ID
            if (response.session_id) {
                sessionState.sessionId = response.session_id;
            }
            
            // Initialize conversation history
            sessionState.conversationHistory = [{
                role: 'assistant',
                content: response.message || 'Welcome to the health assessment',
                timestamp: new Date().toISOString()
            }];
            
            ui.hideLoadingIndicator();
            handleResponse(response);
            
            // Disable back button initially
            if (backButton) backButton.disabled = true;
            
            // Disable save button initially
            if (saveButton) saveButton.disabled = true;
            
            sessionState.processingResponse = false;
        } catch (error) {
            console.error('Error starting assessment:', error);
            ui.hideLoadingIndicator();
            ui.addMessage('Sorry, there was an error starting the assessment. Please refresh the page and try again.');
            sessionState.processingResponse = false;
        }
    }
    
    // Handle quick assessment mode
    const urlParams = new URLSearchParams(window.location.search);
    const quickMode = urlParams.get('quick');
    
    if (quickMode === 'true') {
        // Show quick assessment UI
        document.querySelector('.quick-assessment-container').style.display = 'block';
        document.querySelector('.chat-container').style.display = 'none';
        
        // Set up quick assessment form
        document.getElementById('quickAssessmentForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (sessionState.processingResponse) {
                return;
            }
            
            const age = document.getElementById('quickAge').value;
            const sex = document.querySelector('input[name="quickSex"]:checked').value;
            const symptomInputs = document.querySelectorAll('.quick-symptom-input');
            
            const symptoms = [];
            symptomInputs.forEach(input => {
                if (input.value.trim()) {
                    symptoms.push(input.value.trim());
                }
            });
            
            if (symptoms.length === 0) {
                alert('Please enter at least one symptom');
                return;
            }
            
            try {
                sessionState.processingResponse = true;
                ui.showLoadingIndicator('Generating quick assessment...');
                
                const response = await api.quickAssessment({
                    age: parseInt(age),
                    biological_sex: sex,
                    symptoms: symptoms
                });
                
                ui.hideLoadingIndicator();
                
                // Switch to chat view and show the report
                document.querySelector('.quick-assessment-container').style.display = 'none';
                document.querySelector('.chat-container').style.display = 'flex';
                
                // Display the report
                ui.addMessage({
                    message: response.message,
                    report: response.report
                });
                
                // Mark assessment as completed
                sessionState.assessmentCompleted = true;
                
                sessionState.processingResponse = false;
            } catch (error) {
                ui.hideLoadingIndicator();
                console.error('Error generating quick assessment:', error);
                alert('Sorry, there was an error generating your assessment. Please try again.');
                sessionState.processingResponse = false;
            }
        });
        
        // Add button to add more symptom inputs
        document.getElementById('addSymptomBtn').addEventListener('click', () => {
            const symptomsContainer = document.querySelector('.quick-symptoms-container');
            const newInput = document.createElement('input');
            newInput.type = 'text';
            newInput.className = 'quick-symptom-input';
            newInput.placeholder = 'Enter another symptom';
            symptomsContainer.appendChild(newInput);
            
            // Add autocomplete to the new input
            setupQuickSymptomAutocomplete(newInput);
        });
        
        // Setup autocomplete for symptom inputs
        function setupQuickSymptomAutocomplete(inputElement) {
            let timeoutId;
            
            inputElement.addEventListener('input', () => {
                clearTimeout(timeoutId);
                
                timeoutId = setTimeout(async () => {
                    const query = inputElement.value.trim();
                    if (query.length < 2) return;
                    
                    try {
                        const results = await api.searchSymptoms(query);
                        showAutocompleteResults(inputElement, results);
                    } catch (error) {
                        console.error('Error searching symptoms:', error);
                    }
                }, 300);
            });
        }
        
        function showAutocompleteResults(inputElement, results) {
            // Remove any existing results
            const existingResults = document.querySelector('.autocomplete-results');
            if (existingResults) {
                existingResults.remove();
            }
            
            if (!results || results.length === 0) return;
            
            // Create results container
            const resultsContainer = document.createElement('div');
            resultsContainer.className = 'autocomplete-results';
            
            // Position the results container
            const inputRect = inputElement.getBoundingClientRect();
            resultsContainer.style.position = 'absolute';
            resultsContainer.style.top = `${inputRect.bottom}px`;
            resultsContainer.style.left = `${inputRect.left}px`;
            resultsContainer.style.width = `${inputRect.width}px`;
            
            // Add results
            results.slice(0, 5).forEach(result => {
                const resultItem = document.createElement('div');
                resultItem.className = 'autocomplete-item';
                resultItem.textContent = result.name;
                
                resultItem.addEventListener('click', () => {
                    inputElement.value = result.name;
                    resultsContainer.remove();
                });
                
                resultsContainer.appendChild(resultItem);
            });
            
            document.body.appendChild(resultsContainer);
            
            // Close results when clicking outside
            document.addEventListener('click', (e) => {
                if (!resultsContainer.contains(e.target) && e.target !== inputElement) {
                    resultsContainer.remove();
                }
            });
        }
        
        // Setup initial symptom inputs
        const initialInputs = document.querySelectorAll('.quick-symptom-input');
        initialInputs.forEach(input => {
            setupQuickSymptomAutocomplete(input);
        });
        
    } else {
        // Normal assessment mode
        // Initialize the chat
        startAssessment();
    }
    
    // Handle window resize for mobile responsiveness
    window.addEventListener('resize', () => {
        ui.adjustLayoutForScreenSize();
    });
    
    
});
