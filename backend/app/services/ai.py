import os
import re
import datetime
import google.generativeai as genai

class AIService:
    """Service for AI-powered health assessments with enhanced symptom interpretation"""
    
    def __init__(self):
        """Initialize the AI service with the Gemini API"""
        api_key = os.environ.get('GEMINI_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
        self.model = None
        try:
            # Using gemini-1.5-flash for faster generation
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            # Configure generation parameters for faster response
            self.generation_config = {
                "temperature": 0.3,  # Lower temperature for more focused outputs
                "top_p": 0.8,        # More deterministic responses
                "top_k": 40,         # Limit token selection for faster generation
                "max_output_tokens": 1024  # Limit output size for faster generation
            }
        except Exception as e:
            print(f"Error initializing Gemini model: {e}")
    
    def generate_assessment(self, name, age, biological_sex, symptoms, answers):
        """Generate a health assessment based on symptoms and answers"""
        if not self.model:
            return self._generate_fallback_assessment(name, symptoms)
        
        try:
            # Format the gathered info for the AI
            symptoms_str = ", ".join(symptoms)
            
            # Format answers into a readable string with better organization
            medical_history = []
            lifestyle_factors = []
            symptom_details = []
            medications = []
            
            for k, v in answers.items():
                if k not in ['name', 'age', 'biological_sex']:
                    if k.startswith('medical_history'):
                        medical_history.append(f"- {k.replace('medical_history_', '')}: {v}")
                    elif k.startswith('lifestyle'):
                        lifestyle_factors.append(f"- {k.replace('lifestyle_factors_', '')}: {v}")
                    elif k in ['medications', 'allergies']:
                        medications.append(f"- {k}: {v}")
                    else:
                        symptom_details.append(f"- {k}: {v}")
            
            # Create organized sections for the prompt
            medical_history_str = "\n".join(medical_history) if medical_history else "None reported"
            lifestyle_str = "\n".join(lifestyle_factors) if lifestyle_factors else "None reported"
            medications_str = "\n".join(medications) if medications else "None reported"
            symptom_details_str = "\n".join(symptom_details) if symptom_details else "No additional details"
            
            # Get current date for the report
            current_date = datetime.datetime.now().strftime("%B %d, %Y")
            
            # Enhanced prompt for more structured assessment with urgency levels and condition likelihoods
            prompt = f"""
            You are an expert medical assistant creating a comprehensive health assessment report. Follow this structured format exactly:

            PATIENT: {name}, {age} years old, {biological_sex}
            DATE: {current_date}
            SYMPTOMS: {symptoms_str}
            
            Based on this information and the details below, generate a structured clinical report:
            
            SYMPTOM DETAILS:
            {symptom_details_str}
            
            MEDICAL HISTORY:
            {medical_history_str}
            
            MEDICATIONS AND ALLERGIES:
            {medications_str}
            
            LIFESTYLE FACTORS:
            {lifestyle_str}
            
            FORMAT YOUR RESPONSE WITH THESE EXACT SECTIONS:
            
            1. SUMMARY: Begin with "Assessment for {name}:" followed by a concise paragraph (3-4 sentences) analyzing likely causes of symptoms based on patient profile. Focus on clinical relevance.
            
            2. SYMPTOM ANALYSIS: List each reported symptom with its characteristics (duration, severity, pattern). Format as "Symptom: Duration, Severity, Pattern, Associated factors".
            
            3. POSSIBLE CONDITIONS: List exactly 3-5 conditions in order of likelihood with percentage estimates. For each condition include:
               - Condition name
               - Likelihood percentage (e.g., 70%)
               - Urgency level (Requires immediate attention, Requires prompt attention, Routine care recommended, Self-care appropriate)
               - Brief explanation of why this matches symptoms (one sentence)
               - Key symptoms supporting this diagnosis
            
            4. WARNING SIGNS: List 4-6 specific symptoms that would require immediate medical attention.
            
            5. RECOMMENDED NEXT STEPS: Provide clear guidance with specific timeframes (e.g., "within 24 hours," "within 1 week") and urgency levels.
            
            6. SELF-CARE: Provide 4-6 practical, evidence-based recommendations with specific details.
            
            7. PREVENTION: List 4-6 targeted measures to prevent recurrence or worsening.
            
            Use plain, direct language. Avoid medical jargon when possible. Do not use markdown formatting.
            """
            
            # Generate content with optimized parameters
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            # Process the response into a structured format
            assessment_text = response.text
            
            # Parse the text into enhanced sections
            sections = self._parse_assessment_into_sections(assessment_text)
            
            # Add metadata to the report
            sections["report_date"] = current_date
            sections["report_id"] = f"HA-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            return sections
            
        except Exception as e:
            print(f"Error generating assessment: {e}")
            return self._generate_fallback_assessment(name, symptoms)
    
    def _parse_assessment_into_sections(self, text):
        """Parse the assessment text into structured sections with enhanced organization"""
        # Enhanced sections structure
        sections = {
            "summary": "",
            "symptom_analysis": [],
            "possible_conditions": [],
            "warning_signs": [],
            "next_steps": "",
            "self_care": [],
            "prevention": []
        }
        
        current_section = "summary"
        condition_details = {}
        urgency_levels = {}
        likelihood_percentages = {}
        supporting_symptoms = {}
        current_condition = None
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Clean up markdown formatting
            line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)  # Remove bold markers
            line = re.sub(r'\*(.*?)\*', r'\1', line)      # Remove italic markers
            line = re.sub(r'^\d+\.\s+', '', line)         # Remove numbered list markers
            
            # Check for section headers
            lower_line = line.lower()
            if "summary" in lower_line and len(line) < 30:
                current_section = "summary"
                continue
            elif "symptom analysis" in lower_line:
                current_section = "symptom_analysis"
                continue
            elif "possible conditions" in lower_line or "conditions" in lower_line and "possible" in lower_line:
                current_section = "possible_conditions"
                continue
            elif "warning signs" in lower_line or "red flags" in lower_line:
                current_section = "warning_signs"
                continue
            elif "next steps" in lower_line or "recommended" in lower_line and "steps" in lower_line:
                current_section = "next_steps"
                continue
            elif "self-care" in lower_line or "self care" in lower_line:
                current_section = "self_care"
                continue
            elif "prevention" in lower_line or "preventive" in lower_line:
                current_section = "prevention"
                continue
            
            # Process content based on section
            if current_section == "symptom_analysis":
                if (line.startswith("- ") or line.startswith("• ") or line.startswith("* ")):
                    sections["symptom_analysis"].append(line[2:].strip())
                elif sections["symptom_analysis"] and not line.lower().startswith("symptom"):
                    # Append to the last item if it's a continuation
                    sections["symptom_analysis"][-1] += " " + line
            
            elif current_section == "possible_conditions":
                # Extract condition, likelihood, urgency, and explanation
                if (line.startswith("- ") or line.startswith("• ") or line.startswith("* ")):
                    line = line[2:].strip()
                    
                    # Check for condition name
                    condition_match = re.match(r'^(.*?)(?:\s*\(|:|\s+\d+%|$)', line)
                    if condition_match:
                        condition_name = condition_match.group(1).strip()
                        current_condition = condition_name
                        sections["possible_conditions"].append(condition_name)
                        
                        # Extract likelihood percentage
                        likelihood_match = re.search(r'(\d+)%', line)
                        if likelihood_match:
                            likelihood_percentages[condition_name] = int(likelihood_match.group(1))
                        
                        # Extract urgency level
                        urgency_patterns = [
                            r'requires immediate attention', 
                            r'requires prompt attention', 
                            r'routine care recommended',
                            r'self-care appropriate'
                        ]
                        
                        for pattern in urgency_patterns:
                            if re.search(pattern, line.lower()):
                                urgency_levels[condition_name] = pattern
                                break
                        
                        # Extract explanation
                        explanation_match = re.search(r'(?::|;)\s*(.*?)(?:\.|$)', line)
                        if explanation_match:
                            condition_details[condition_name] = explanation_match.group(1).strip()
                
                # Check for supporting symptoms
                elif current_condition and ("supporting symptoms" in line.lower() or "key symptoms" in line.lower()):
                    supporting_symptoms[current_condition] = []
                elif current_condition and supporting_symptoms.get(current_condition) is not None:
                    if line.startswith("- ") or line.startswith("• ") or line.startswith("* "):
                        supporting_symptoms[current_condition].append(line[2:].strip())
                    
            elif current_section in ["warning_signs", "self_care", "prevention"]:
                if (line.startswith("- ") or line.startswith("• ") or line.startswith("* ")):
                    sections[current_section].append(line[2:].strip())
                elif sections[current_section] and not line.lower().startswith(("warning", "self", "prevent")):
                    # Append to the last item if it's a continuation
                    sections[current_section][-1] += " " + line
            else:
                if current_section in ["summary", "next_steps"]:
                    if sections[current_section]:
                        sections[current_section] += " " + line
                    else:
                        sections[current_section] = line
        
        # Add the enhanced condition details to the output
        if condition_details:
            sections["condition_details"] = condition_details
        if urgency_levels:
            sections["urgency_levels"] = urgency_levels
        if likelihood_percentages:
            sections["likelihood_percentages"] = likelihood_percentages
        if supporting_symptoms:
            sections["supporting_symptoms"] = supporting_symptoms
        
        # If prevention section is empty, generate a basic one
        if not sections["prevention"]:
            sections["prevention"] = self._generate_basic_prevention(sections["possible_conditions"])
        
        # Ensure we have at least some content in each section
        for section in ["warning_signs", "self_care"]:
            if not sections[section]:
                sections[section] = self._generate_fallback_section(section, symptoms=sections["possible_conditions"])
        
        return sections
    
    def _generate_basic_prevention(self, conditions):
        """Generate basic prevention measures based on conditions"""
        prevention = [
            "Maintain a balanced diet rich in fruits, vegetables, and whole grains",
            "Stay hydrated by drinking adequate water throughout the day",
            "Get regular physical activity appropriate for your condition",
            "Ensure adequate sleep (7-9 hours for most adults)",
            "Manage stress through relaxation techniques or mindfulness practices"
        ]
        
        # Add condition-specific prevention if available
        condition_prevention = {
            "Common Cold": ["Wash hands frequently", "Avoid close contact with sick individuals", "Disinfect frequently touched surfaces"],
            "Influenza": ["Consider annual flu vaccination", "Practice good respiratory hygiene", "Avoid crowded places during flu season"],
            "Migraine": ["Identify and avoid personal triggers", "Maintain a regular sleep schedule", "Stay hydrated"],
            "Hypertension": ["Limit sodium intake", "Maintain a healthy weight", "Limit alcohol consumption"],
            "Gastroenteritis": ["Practice proper food handling and storage", "Wash hands thoroughly before meals", "Avoid undercooked foods"],
            "Anxiety": ["Practice regular relaxation techniques", "Limit caffeine and alcohol", "Maintain social connections"],
            "Depression": ["Stay physically active", "Maintain social connections", "Establish a regular daily routine"],
            "Asthma": ["Avoid known triggers", "Take medications as prescribed", "Create an asthma action plan"],
            "Allergic Rhinitis": ["Monitor pollen counts", "Keep windows closed during high pollen seasons", "Use air purifiers"],
            "Upper Respiratory Infection": ["Rest adequately", "Use a humidifier", "Avoid smoking and secondhand smoke"],
            "Bronchitis": ["Avoid irritants like smoke", "Use a humidifier", "Stay up to date on vaccinations"],
            "Sinusitis": ["Use a saline nasal spray", "Apply warm compresses to the face", "Sleep with your head elevated"],
            "Gastritis": ["Eat smaller, more frequent meals", "Avoid spicy or acidic foods", "Limit alcohol consumption"],
            "Tension Headache": ["Practice good posture", "Take regular breaks from screens", "Use stress management techniques"],
            "Insomnia": ["Maintain a regular sleep schedule", "Create a restful sleep environment", "Avoid screens before bedtime"]
        }
        
        for condition in conditions:
            for known_condition, measures in condition_prevention.items():
                if known_condition.lower() in condition.lower():
                    prevention.extend(measures)
                    break
        
        # Remove duplicates while preserving order
        unique_prevention = []
        seen = set()
        for item in prevention:
            if item.lower() not in seen:
                seen.add(item.lower())
                unique_prevention.append(item)
        
        return unique_prevention[:6]  # Limit to 6 prevention measures
    
    def _generate_fallback_section(self, section_type, symptoms=None):
        """Generate fallback content for a section if it's empty"""
        if section_type == "warning_signs":
            return [
                "Severe or worsening symptoms that interfere with daily activities",
                "Difficulty breathing or shortness of breath",
                "High fever (above 101.5°F or 38.6°C) that persists for more than 24 hours",
                "Severe pain that is not relieved by over-the-counter medications",
                "New confusion or inability to stay alert"
            ]
        elif section_type == "self_care":
            return [
                "Rest as needed and avoid strenuous activities until symptoms improve",
                "Stay hydrated by drinking water, herbal tea, or clear broths",
                "Take over-the-counter pain relievers as directed for pain or fever",
                "Use a cool compress if experiencing localized pain or inflammation",
                "Monitor your symptoms and keep a log of any changes"
            ]
        return []
    
    def _generate_fallback_assessment(self, name, symptoms):
        """Generate a comprehensive fallback assessment when AI is unavailable"""
        main_symptom = symptoms[0] if symptoms else "your symptoms"
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        
        return {
            "report_date": current_date,
            "report_id": f"HA-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "summary": f"Assessment for {name}: Based on your report of {main_symptom}, we recommend consulting with a healthcare professional for a proper diagnosis. Your symptoms could be related to several possible conditions that require professional evaluation.",
            "symptom_analysis": [
                f"{main_symptom}: Duration unknown, Severity unknown, Pattern unknown"
            ],
            "next_steps": "Schedule an appointment with your primary care physician within the next 7 days to discuss your symptoms. If your symptoms worsen significantly before your appointment, consider seeking urgent care services.",
            "possible_conditions": [
                "Common causes of " + main_symptom,
                "Inflammatory conditions",
                "Temporary viral or bacterial infection"
            ],
            "condition_details": {
                "Common causes of " + main_symptom: "Several common conditions can cause these symptoms. A healthcare provider can perform the necessary examination and tests to determine the specific cause.",
                "Inflammatory conditions": "Some inflammatory conditions can present with these symptoms and may require specific treatment approaches.",
                "Temporary viral or bacterial infection": "Many infections can cause similar symptoms and typically resolve with appropriate treatment and rest."
            },
            "urgency_levels": {
                "Common causes of " + main_symptom: "routine care recommended",
                "Inflammatory conditions": "requires prompt attention",
                "Temporary viral or bacterial infection": "self-care appropriate"
            },
            "likelihood_percentages": {
                "Common causes of " + main_symptom: 60,
                "Inflammatory conditions": 25,
                "Temporary viral or bacterial infection": 15
            },
            "supporting_symptoms": {
                "Common causes of " + main_symptom: [main_symptom],
                "Inflammatory conditions": [main_symptom],
                "Temporary viral or bacterial infection": [main_symptom]
            },
            "warning_signs": [
                "Severe or worsening symptoms that interfere with daily activities",
                "Difficulty breathing or shortness of breath",
                "High fever (above 101.5°F or 38.6°C) that persists for more than 24 hours",
                "Severe pain that is not relieved by over-the-counter medications",
                "New confusion or inability to stay alert"
            ],
            "self_care": [
                "Rest as needed and avoid strenuous activities until symptoms improve",
                "Stay hydrated by drinking water, herbal tea, or clear broths",
                "Take over-the-counter pain relievers like acetaminophen or ibuprofen as directed for pain or fever",
                "Use a cool compress if experiencing localized pain or inflammation",
                "Monitor your symptoms and keep a log of any changes"
            ],
            "prevention": [
                "Wash hands frequently with soap and water for at least 20 seconds",
                "Maintain a balanced diet rich in fruits, vegetables, and whole grains",
                "Stay physically active with regular exercise appropriate to your condition",
                "Manage stress through relaxation techniques, meditation, or deep breathing",
                "Get adequate sleep on a regular schedule"
            ]
        }
