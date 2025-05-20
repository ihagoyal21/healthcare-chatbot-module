class ApiService {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.sessionId = null;
    }

    async startAssessment() {
        try {
            const response = await fetch(`${this.baseUrl}/api/assessment/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            this.sessionId = data.session_id;
            return data;
        } catch (error) {
            console.error('Error starting assessment:', error);
            throw error;
        }
    }

    async sendMessage(input) {
        if (!this.sessionId) {
            throw new Error('No active session. Please start an assessment first.');
        }

        try {
            const response = await fetch(`${this.baseUrl}/api/assessment/next`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    input: input
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }

    async searchSymptoms(query) {
        try {
            const response = await fetch(`${this.baseUrl}/api/symptoms/search?q=${encodeURIComponent(query)}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error searching symptoms:', error);
            throw error;
        }
    }
}
