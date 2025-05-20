from flask import Blueprint, request, jsonify, current_app, make_response
import uuid
import datetime
import hashlib
import json
from app import cache  # Import cache from app module
from app.services.assessment import AssessmentService
from app.services.ai import AIService

main = Blueprint('main', __name__)

# Initialize services
assessment_service = AssessmentService()
ai_service = AIService()

# Store active sessions (in production, use Redis or a database)
sessions = {}

# Performance monitoring
@main.before_request
def before_request():
    request.start_time = datetime.datetime.now()

@main.after_request
def after_request(response):
    if hasattr(request, 'start_time'):
        elapsed = datetime.datetime.now() - request.start_time
        current_app.logger.info(f"Request to {request.path} took {elapsed.total_seconds():.2f}s")
    
    # Add cache headers for appropriate endpoints
    if request.path.startswith('/api/symptoms/search'):
        response.headers['Cache-Control'] = 'public, max-age=3600'
    
    return response

@main.route('/')
def index():
    """Root endpoint with API information"""
    return jsonify({
        "message": "Healthcare Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "health_check": "/api/health",
            "start_assessment": "/api/assessment/start",
            "process_input": "/api/assessment/next",
            "search_symptoms": "/api/symptoms/search",
            "quick_assessment": "/api/assessment/quick",
            "start_new": "/api/assessment/start_new"
        }
    })

@main.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

@main.route('/api/assessment/start', methods=['POST'])
def start_assessment():
    """Start a new symptom assessment"""
    session_id = str(uuid.uuid4())
    
    # Initialize session with more detailed structure
    sessions[session_id] = {
        "current_state": "introduction",
        "previous_state": None,
        "state_history": [],
        "gathered_info": {
            "assessment_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "medical_history": {},
            "current_medications": [],
            "allergies": [],
            "family_history": {},
            "lifestyle_factors": {}
        },
        "symptoms": [],
        "symptom_details": {},
        "progress": 0,
        "conversation_history": [],
        "current_flow": "main",  # Track which conversation flow we're in
        "flow_position": 0,      # Position within the current flow
        "pending_questions": [],  # Queue of follow-up questions
        "symptom_specific_flow": None  # Track symptom-specific flow
    }
    
    return jsonify({
        "session_id": session_id,
        "message": "Hi, I'm your health assistant. I'll ask you several detailed questions about your symptoms to provide a comprehensive assessment. This is not a substitute for professional medical advice, but I can help guide you. Shall we begin?",
        "options": ["Yes, let's start", "What information will you collect?"],
        "progress": 0
    })

@main.route('/api/assessment/start_new', methods=['POST'])
def start_new_assessment():
    """Start a new assessment while preserving the previous session ID"""
    data = request.json
    old_session_id = data.get('session_id')
    
    # Generate a new session ID
    new_session_id = str(uuid.uuid4())
    
    # Initialize a new session
    sessions[new_session_id] = {
        "current_state": "introduction",
        "previous_state": None,
        "state_history": [],
        "gathered_info": {
            "assessment_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "medical_history": {},
            "current_medications": [],
            "allergies": [],
            "family_history": {},
            "lifestyle_factors": {}
        },
        "symptoms": [],
        "symptom_details": {},
        "progress": 0,
        "conversation_history": [],
        "current_flow": "main",
        "flow_position": 0,
        "pending_questions": [],
        "symptom_specific_flow": None
    }
    
    # If there was a previous session, we can optionally archive it or transfer some data
    if old_session_id and old_session_id in sessions:
        # Optionally preserve some data from the old session if needed
        # For example: sessions[new_session_id]["user_preferences"] = sessions[old_session_id].get("user_preferences", {})
        
        # For privacy reasons, we might want to eventually clean up old sessions
        # This could be done asynchronously in a production environment
        # sessions.pop(old_session_id, None)
        pass
    
    return jsonify({
        "session_id": new_session_id,
        "message": "Starting a new health assessment. I'll ask you several detailed questions about your symptoms to provide a comprehensive assessment. This is not a substitute for professional medical advice, but I can help guide you. Shall we begin?",
        "options": ["Yes, let's start", "What information will you collect?"],
        "progress": 0
    })

@main.route('/api/assessment/next', methods=['POST'])
def process_input():
    """Process user input and return next step with enhanced flow management"""
    data = request.json
    session_id = data.get('session_id')
    user_input = data.get('input')
    
    if not session_id or session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 400
    
    session = sessions[session_id]
    current_state = session["current_state"]
    
    # Store conversation history
    session["conversation_history"].append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Save previous state for potential backtracking
    session["previous_state"] = current_state
    session["state_history"].append(current_state)
    
    # Check if we're in a symptom-specific flow
    if session["symptom_specific_flow"] and session["current_flow"] == "symptom_specific":
        return handle_symptom_specific_flow(session, user_input)
    
    # Process based on current state in main flow
    if current_state == "introduction":
        if user_input == "What information will you collect?":
            response = {
                "message": "I'll ask about your personal details (name, age, sex), medical history, current symptoms, their severity and duration, and lifestyle factors. This helps me provide a more accurate assessment. All information is kept confidential. Would you like to proceed?",
                "options": ["Yes, let's start", "No, maybe later"],
                "progress": 0
            }
        else:
            session["current_state"] = "name"
            response = {
                "message": "Great! First, what's your name? This helps me personalize our conversation.",
                "input_type": "text",
                "progress": 5
            }
    
    elif current_state == "name":
        session["gathered_info"]["name"] = user_input
        session["current_state"] = "age"
        response = {
            "message": f"Nice to meet you, {user_input}. How old are you? Your age helps me understand which conditions might be more relevant to you.",
            "input_type": "number",
            "progress": 8
        }
    
    elif current_state == "age":
        try:
            age = int(user_input)
            if age < 0 or age > 120:
                return jsonify({
                    "message": "Please enter a valid age between 0 and 120.",
                    "input_type": "number",
                    "progress": 8
                })
        except ValueError:
            return jsonify({
                "message": "Please enter a valid number for your age.",
                "input_type": "number",
                "progress": 8
            })
        
        session["gathered_info"]["age"] = age
        session["current_state"] = "biological_sex"
        
        response = {
            "message": "What is your biological sex? This is important as certain medical conditions affect biological sexes differently.",
            "options": ["Female", "Male", "Intersex"],
            "info_button": {
                "title": "Why is this important?",
                "content": "Biological sex affects how symptoms present and which conditions are more likely. For example, heart attack symptoms often differ between males and females."
            },
            "progress": 12
        }
    
    elif current_state == "biological_sex":
        session["gathered_info"]["biological_sex"] = user_input
        
        # Branching logic based on biological sex and age
        if user_input.lower() == "female" and 12 <= session["gathered_info"].get("age", 0) <= 55:
            session["current_state"] = "pregnancy"
            response = {
                "message": "Are you currently pregnant or is there a possibility you might be pregnant?",
                "options": ["Yes", "No", "Possibly", "I'm not sure"],
                "progress": 16
            }
        else:
            session["current_state"] = "height_weight"
            response = {
                "message": "What is your height and weight? This helps assess your body mass index (BMI), which can be relevant for certain conditions.",
                "input_type": "text",
                "placeholder": "e.g., 5'10\", 160 lbs or 178 cm, 73 kg",
                "progress": 16
            }
    
    elif current_state == "pregnancy":
        session["gathered_info"]["pregnancy_status"] = user_input
        session["current_state"] = "height_weight"
        response = {
            "message": "What is your height and weight? This helps assess your body mass index (BMI), which can be relevant for certain conditions.",
            "input_type": "text",
            "placeholder": "e.g., 5'10\", 160 lbs or 178 cm, 73 kg",
            "progress": 20
        }
    
    elif current_state == "height_weight":
        session["gathered_info"]["height_weight"] = user_input
        session["current_state"] = "medical_history_intro"
        response = {
            "message": "Now I'll ask about your medical history. This information helps provide context for your current symptoms. Do you have any diagnosed medical conditions?",
            "options": ["Yes", "No"],
            "progress": 24
        }
    
    elif current_state == "medical_history_intro":
        if user_input.lower() == "yes":
            session["current_state"] = "medical_history_conditions"
            response = {
                "message": "Please select any conditions you've been diagnosed with:",
                "options": [
                    "Diabetes", "High blood pressure", "Heart disease", "Asthma", 
                    "COPD", "Cancer", "Thyroid disorder", "Autoimmune disease",
                    "Kidney disease", "Liver disease", "Mental health condition",
                    "Neurological disorder", "Other condition"
                ],
                "multiple_select": True,
                "progress": 28
            }
        else:
            session["current_state"] = "medications"
            response = {
                "message": "Are you currently taking any medications, including prescription, over-the-counter, supplements, or herbal remedies?",
                "options": ["Yes", "No"],
                "progress": 32
            }
    
    elif current_state == "medical_history_conditions":
        session["gathered_info"]["medical_history"]["conditions"] = user_input
        
        # If "Other condition" is selected, ask for details
        if "Other condition" in user_input:
            session["current_state"] = "medical_history_other"
            response = {
                "message": "You mentioned having another condition. Could you please specify what it is?",
                "input_type": "text",
                "progress": 32
            }
        else:
            session["current_state"] = "medications"
            response = {
                "message": "Are you currently taking any medications, including prescription, over-the-counter, supplements, or herbal remedies?",
                "options": ["Yes", "No"],
                "progress": 32
            }
    
    elif current_state == "medical_history_other":
        session["gathered_info"]["medical_history"]["other_condition"] = user_input
        session["current_state"] = "medications"
        response = {
            "message": "Are you currently taking any medications, including prescription, over-the-counter, supplements, or herbal remedies?",
            "options": ["Yes", "No"],
            "progress": 32
        }
    
    elif current_state == "medications":
        if user_input.lower() == "yes":
            session["current_state"] = "medications_list"
            response = {
                "message": "Please list the medications you're taking. Include the name, dosage if known, and how often you take them.",
                "input_type": "text",
                "placeholder": "e.g., Lisinopril 10mg daily, Vitamin D 1000IU daily",
                "progress": 36
            }
        else:
            session["gathered_info"]["medications"] = "None"
            session["current_state"] = "allergies"
            response = {
                "message": "Do you have any allergies to medications, foods, or environmental factors?",
                "options": ["Yes", "No"],
                "progress": 40
            }
    
    elif current_state == "medications_list":
        session["gathered_info"]["medications"] = user_input
        session["current_state"] = "allergies"
        response = {
            "message": "Do you have any allergies to medications, foods, or environmental factors?",
            "options": ["Yes", "No"],
            "progress": 40
        }
    
    elif current_state == "allergies":
        if user_input.lower() == "yes":
            session["current_state"] = "allergies_list"
            response = {
                "message": "Please list your allergies and any reactions you experience:",
                "input_type": "text",
                "placeholder": "e.g., Penicillin (rash), Peanuts (anaphylaxis)",
                "progress": 44
            }
        else:
            session["gathered_info"]["allergies"] = "None"
            session["current_state"] = "family_history"
            response = {
                "message": "Do any medical conditions run in your family? Family history can be relevant for many health issues.",
                "options": ["Yes", "No", "I don't know"],
                "progress": 48
            }
    
    elif current_state == "allergies_list":
        session["gathered_info"]["allergies"] = user_input
        session["current_state"] = "family_history"
        response = {
            "message": "Do any medical conditions run in your family? Family history can be relevant for many health issues.",
            "options": ["Yes", "No", "I don't know"],
            "progress": 48
        }
    
    elif current_state == "family_history":
        if user_input.lower() == "yes":
            session["current_state"] = "family_history_details"
            response = {
                "message": "Please select any conditions that run in your immediate family (parents, siblings, children):",
                "options": [
                    "Heart disease", "Diabetes", "Cancer", "High blood pressure", 
                    "Stroke", "Mental health conditions", "Autoimmune disorders",
                    "Other condition"
                ],
                "multiple_select": True,
                "progress": 52
            }
        else:
            session["gathered_info"]["family_history"] = user_input
            session["current_state"] = "lifestyle_smoking"
            response = {
                "message": "Do you smoke tobacco or use e-cigarettes/vaping products?",
                "options": ["Currently smoke", "Used to smoke", "Never smoked", "Use e-cigarettes/vape"],
                "progress": 56
            }
    
    elif current_state == "family_history_details":
        session["gathered_info"]["family_history"] = user_input
        session["current_state"] = "lifestyle_smoking"
        response = {
            "message": "Do you smoke tobacco or use e-cigarettes/vaping products?",
            "options": ["Currently smoke", "Used to smoke", "Never smoked", "Use e-cigarettes/vape"],
            "progress": 56
        }
    
    elif current_state == "lifestyle_smoking":
        session["gathered_info"]["lifestyle_factors"]["smoking"] = user_input
        session["current_state"] = "lifestyle_alcohol"
        response = {
            "message": "How often do you consume alcoholic beverages?",
            "options": ["Never", "Occasionally", "Weekly", "Several times per week", "Daily"],
            "progress": 60
        }
    
    elif current_state == "lifestyle_alcohol":
        session["gathered_info"]["lifestyle_factors"]["alcohol"] = user_input
        session["current_state"] = "lifestyle_exercise"
        response = {
            "message": "How would you describe your physical activity level?",
            "options": ["Sedentary (little to no exercise)", "Light (1-3 days/week)", "Moderate (3-5 days/week)", "Active (6-7 days/week)", "Very active (multiple times daily)"],
            "progress": 64
        }
    
    elif current_state == "lifestyle_exercise":
        session["gathered_info"]["lifestyle_factors"]["exercise"] = user_input
        session["current_state"] = "lifestyle_diet"
        response = {
            "message": "How would you describe your diet?",
            "options": ["Balanced diet", "Vegetarian", "Vegan", "Keto/low-carb", "High protein", "Restricted due to allergies/conditions", "Irregular eating patterns"],
            "progress": 68
        }
    
    elif current_state == "lifestyle_diet":
        session["gathered_info"]["lifestyle_factors"]["diet"] = user_input
        session["current_state"] = "lifestyle_stress"
        response = {
            "message": "How would you rate your current stress level?",
            "options": ["Low", "Moderate", "High", "Very high"],
            "progress": 72
        }
    
    elif current_state == "lifestyle_stress":
        session["gathered_info"]["lifestyle_factors"]["stress"] = user_input
        session["current_state"] = "lifestyle_sleep"
        response = {
            "message": "How many hours of sleep do you typically get per night?",
            "options": ["Less than 5 hours", "5-6 hours", "7-8 hours", "More than 8 hours", "Irregular sleep pattern"],
            "progress": 76
        }
    
    elif current_state == "lifestyle_sleep":
        session["gathered_info"]["lifestyle_factors"]["sleep"] = user_input
        session["current_state"] = "symptom_entry"
        response = {
            "message": "Now, let's focus on why you're seeking help today. What's the main symptom that's bothering you?",
            "input_type": "symptom_search",
            "placeholder": "e.g., headache, cough, stomach pain",
            "progress": 80
        }
    
    elif current_state == "symptom_entry":
        # Add the symptom to the list
        primary_symptom = user_input
        session["symptoms"].append(primary_symptom)
        
        # Transition to symptom-specific flow
        session["current_flow"] = "symptom_specific"
        session["symptom_specific_flow"] = primary_symptom.lower()
        
        # Get the first question for this symptom
        question = assessment_service.get_first_question(primary_symptom)
        
        # Store current question for reference
        session["current_question"] = question
        
        # Update state to reflect we're in a symptom-specific flow
        session["current_state"] = f"{session['symptom_specific_flow']}_assessment"
        
        # Generate response based on the question
        response = {
            "message": question["text"],
            "options": question["options"] if "options" in question else None,
            "input_type": question.get("input_type", "options"),
            "multiple_select": question.get("multiple_select", False),
            "progress": 84
        }
    
    # Add handling for additional symptoms state
    elif current_state == "additional_symptoms":
        # Check if user selected "None of these"
        if user_input == "None of these":
            # No additional symptoms, proceed to impact assessment
            session["current_state"] = "symptom_impact"
            response = {
                "message": f"How much are your symptoms affecting your daily activities?",
                "options": [
                    "Not at all", 
                    "Slightly limiting", 
                    "Moderately limiting", 
                    "Severely limiting", 
                    "Completely unable to perform normal activities"
                ],
                "progress": 94
            }
        elif user_input == "Other symptoms":
            # User wants to enter custom symptoms
            session["current_state"] = "other_symptoms"
            response = {
                "message": "Please describe any other symptoms you're experiencing:",
                "input_type": "text",
                "progress": 94
            }
        else:
            # User selected one or more symptoms from the list
            # Add these symptoms to the list
            if isinstance(user_input, list):
                session["symptoms"].extend(user_input)
            else:
                # Handle comma-separated string of symptoms
                additional_symptoms = [s.strip() for s in user_input.split(',')]
                session["symptoms"].extend(additional_symptoms)
            
            # Proceed to impact assessment
            session["current_state"] = "symptom_impact"
            response = {
                "message": f"How much are your symptoms affecting your daily activities?",
                "options": [
                    "Not at all", 
                    "Slightly limiting", 
                    "Moderately limiting", 
                    "Severely limiting", 
                    "Completely unable to perform normal activities"
                ],
                "progress": 94
            }
    
    elif current_state == "other_symptoms":
        # Process custom symptoms entered by the user
        other_symptoms = [s.strip() for s in user_input.split(',')]
        session["symptoms"].extend(other_symptoms)
        
        # Move to impact assessment
        session["current_state"] = "symptom_impact"
        response = {
            "message": f"How much are your symptoms affecting your daily activities?",
            "options": [
                "Not at all", 
                "Slightly limiting", 
                "Moderately limiting", 
                "Severely limiting", 
                "Completely unable to perform normal activities"
            ],
            "progress": 94
        }
    
    elif current_state == "symptom_impact":
        session["symptom_details"]["impact"] = user_input
        session["current_state"] = "previous_treatment"
        
        response = {
            "message": "Have you tried any treatments or remedies for these symptoms?",
            "options": ["No treatment tried", "Over-the-counter medication", "Prescription medication", "Home remedies", "Rest/lifestyle changes", "Other"],
            "multiple_select": True,
            "progress": 98
        }
    
    elif current_state == "previous_treatment":
        session["symptom_details"]["previous_treatment"] = user_input
        session["current_state"] = "results"
        
        response = {
            "message": "Thank you for providing all this information. I now have enough details to generate your health assessment report.",
            "options": ["View my assessment report"],
            "progress": 99
        }
    
    elif current_state == "results":
        # Generate assessment
        results = ai_service.generate_assessment(
            name=session["gathered_info"].get("name", ""),
            age=session["gathered_info"].get("age"),
            biological_sex=session["gathered_info"].get("biological_sex"),
            symptoms=session["symptoms"],
            answers={
                **session["gathered_info"],
                **session["symptom_details"]
            }
        )
        
        # Add specialist recommendations based on symptoms
        specialists = get_recommended_specialists(session["symptoms"])
        if specialists:
            results["specialists"] = specialists
        
        # Add timestamp to results
        results["generated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Add a start new assessment option
        response = {
            "message": f"Here's your comprehensive health assessment, {session['gathered_info'].get('name', '')}.",
            "report": results,
            "progress": 100,
            "show_start_new": True  # Flag to show start new assessment button
        }
    
    else:
        # Default fallback
        response = {
            "message": "I'm not sure how to proceed. Let's start over.",
            "options": ["Start over"],
            "progress": 0
        }
    
    # Store bot response in conversation history
    session["conversation_history"].append({
        "role": "assistant",
        "content": response.get("message", ""),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    return jsonify(response)

def handle_symptom_specific_flow(session, user_input):
    """Handle symptom-specific conversation flows"""
    current_state = session["current_state"]
    primary_symptom = session["symptom_specific_flow"]
    
    # Store the answer to the current question
    if "current_question" in session and session["current_question"]:
        question_id = session["current_question"].get("id", "unknown")
        session["symptom_details"][question_id] = user_input
        
        # Store the last answered question to prevent repetition
        session["last_answered_question_id"] = question_id
    
    # Get the next question based on the symptom and previous answers
    next_question = assessment_service.get_next_question(
        primary_symptom, 
        session["symptom_details"]
    )
    
    # If we have more questions, continue the symptom-specific flow
    if next_question:
        # Check if this is the same as the last question to prevent repetition
        if "last_question_text" in session and session.get("last_question_text") == next_question["text"]:
            # Skip to additional symptoms if we're repeating questions
            session["current_flow"] = "main"
            session["current_state"] = "additional_symptoms"
            
            # Get related symptoms based on the primary symptom
            related_symptoms = assessment_service.get_related_symptoms(primary_symptom)
            
            response = {
                "message": "Are you experiencing any other symptoms along with your main concern?",
                "options": related_symptoms + ["None of these", "Other symptoms"],
                "multiple_select": True,
                "progress": 92
            }
        else:
            # Store the current question for reference
            session["current_question"] = next_question
            # Store the question text to check for repetition next time
            session["last_question_text"] = next_question["text"]
            
            response = {
                "message": next_question["text"],
                "options": next_question.get("options"),
                "input_type": next_question.get("input_type", "options"),
                "multiple_select": next_question.get("multiple_select", False),
                "progress": min(95, 84 + len(session["symptom_details"]) * 2)  # Increment progress
            }
    else:
        # If no more symptom-specific questions, ask about additional symptoms
        session["current_flow"] = "main"  # Return to main flow
        session["current_state"] = "additional_symptoms"
        
        # Get related symptoms based on the primary symptom
        related_symptoms = assessment_service.get_related_symptoms(primary_symptom)
        
        response = {
            "message": "Are you experiencing any other symptoms along with your main concern?",
            "options": related_symptoms + ["None of these", "Other symptoms"],
            "multiple_select": True,
            "progress": 92
        }
    
    # Store bot response in conversation history
    session["conversation_history"].append({
        "role": "assistant",
        "content": response.get("message", ""),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    return jsonify(response)

@main.route('/api/assessment/back', methods=['POST'])
def go_back_in_conversation():
    """Allow users to go back to a previous question"""
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 400
    
    session = sessions[session_id]
    
    # Check if we have a previous state to go back to
    if not session["state_history"] or len(session["state_history"]) <= 1:
        return jsonify({
            "message": "Cannot go back further. You're at the beginning of the conversation.",
            "error": "no_previous_state"
        }), 400
    
    # Remove the current state from history
    session["state_history"].pop()
    
    # Set the current state to the previous one
    previous_state = session["state_history"][-1]
    session["current_state"] = previous_state
    
    # Generate appropriate response based on the previous state
    # This would need to be implemented based on your state machine
    
    return jsonify({
        "message": "Let's go back to the previous question.",
        "new_state": previous_state
    })

@main.route('/api/assessment/quick', methods=['POST'])
def quick_assessment():
    """Generate a quick assessment for common symptom patterns"""
    data = request.json
    symptoms = data.get('symptoms', [])
    age = data.get('age')
    biological_sex = data.get('biological_sex')
    
    if not symptoms or not age or not biological_sex:
        return jsonify({"error": "Missing required parameters"}), 400
    
    # Generate a simplified assessment without caching for now
    quick_results = ai_service.generate_assessment(
        name="",
        age=age,
        biological_sex=biological_sex,
        symptoms=symptoms,
        answers={}
    )
    
    # Add specialist recommendations
    specialists = get_recommended_specialists(symptoms)
    if specialists:
        quick_results["specialists"] = specialists
    
    # Add timestamp
    quick_results["generated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return jsonify({
        "message": "Here's a quick assessment based on your symptoms.",
        "report": quick_results,
        "show_start_new": True  # Flag to show start new assessment button
    })

@main.route('/api/symptoms/search', methods=['GET'])
def search_symptoms():
    """Search for symptoms based on query"""
    query = request.args.get('q', '')
    results = assessment_service.search_symptoms(query)
    
    response = make_response(jsonify(results))
    response.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours
    return response

@main.route('/api/assessment/save', methods=['POST'])
def save_assessment():
    """Save the current assessment for later reference"""
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id or session_id not in sessions:
        return jsonify({"error": "Invalid session"}), 400
    
    session = sessions[session_id]
    
    # Generate a unique ID for the saved assessment
    saved_id = str(uuid.uuid4())
    
    # Create a snapshot of the current assessment
    assessment_data = {
        "id": saved_id,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_info": {
            "name": session["gathered_info"].get("name", "Anonymous"),
            "age": session["gathered_info"].get("age"),
            "biological_sex": session["gathered_info"].get("biological_sex")
        },
        "symptoms": session["symptoms"],
        "symptom_details": session["symptom_details"],
        "gathered_info": session["gathered_info"],
        "conversation_history": session["conversation_history"]
    }
    
    # In a real application, you would save this to a database
    # For now, we'll just return the ID
    
    return jsonify({
        "message": "Assessment saved successfully",
        "assessment_id": saved_id
    })

def get_recommended_specialists(symptoms):
    """Get recommended specialists based on symptoms"""
    # Map of symptoms to medical specialties
    symptom_to_specialty = {
        "headache": ["Neurologist", "Primary Care Physician"],
        "migraine": ["Neurologist", "Primary Care Physician"],
        "fever": ["Primary Care Physician", "Infectious Disease Specialist"],
        "cough": ["Pulmonologist", "Primary Care Physician"],
        "chest pain": ["Cardiologist", "Emergency Medicine"],
        "shortness of breath": ["Pulmonologist", "Cardiologist"],
        "abdominal pain": ["Gastroenterologist", "Primary Care Physician"],
        "stomach pain": ["Gastroenterologist", "Primary Care Physician"],
        "joint pain": ["Rheumatologist", "Orthopedic Surgeon"],
        "back pain": ["Orthopedic Surgeon", "Neurologist", "Physical Therapist"],
        "rash": ["Dermatologist", "Allergist"],
        "sore throat": ["Otolaryngologist", "Primary Care Physician"],
        "runny nose": ["Allergist", "Otolaryngologist"],
        "dizziness": ["Neurologist", "Otolaryngologist", "Cardiologist"],
        "fatigue": ["Primary Care Physician", "Endocrinologist", "Rheumatologist"],
        "nausea": ["Gastroenterologist", "Primary Care Physician"],
        "vomiting": ["Gastroenterologist", "Emergency Medicine"],
        "diarrhea": ["Gastroenterologist", "Primary Care Physician", "Infectious Disease Specialist"],
        "constipation": ["Gastroenterologist", "Primary Care Physician"],
        "blood in stool": ["Gastroenterologist", "Colorectal Surgeon"],
        "urinary problems": ["Urologist", "Nephrologist"],
        "skin issues": ["Dermatologist"],
        "eye problems": ["Ophthalmologist"],
        "ear pain": ["Otolaryngologist"],
        "hearing loss": ["Audiologist", "Otolaryngologist"],
        "vision changes": ["Ophthalmologist", "Neurologist"],
        "numbness": ["Neurologist"],
        "tingling": ["Neurologist"],
        "weakness": ["Neurologist", "Rheumatologist"],
        "hair loss": ["Dermatologist", "Endocrinologist"],
        "weight loss": ["Primary Care Physician", "Endocrinologist", "Gastroenterologist"],
        "weight gain": ["Primary Care Physician", "Endocrinologist"],
        "anxiety": ["Psychiatrist", "Psychologist"],
        "depression": ["Psychiatrist", "Psychologist"],
        "sleep problems": ["Sleep Specialist", "Neurologist", "Psychiatrist"],
        "memory issues": ["Neurologist", "Geriatrician", "Psychiatrist"],
        "breathing difficulty": ["Pulmonologist", "Cardiologist", "Allergist"],
        "heart palpitations": ["Cardiologist"],
        "swelling": ["Primary Care Physician", "Cardiologist", "Rheumatologist"],
        "joint swelling": ["Rheumatologist", "Orthopedic Surgeon"],
        "muscle pain": ["Rheumatologist", "Orthopedic Surgeon", "Physical Therapist"],
        "watery eyes": ["Ophthalmologist", "Allergist"],
        "sneezing": ["Allergist", "Otolaryngologist", "Primary Care Physician"]
    }
    
    recommended_specialists = {}
    
    for symptom in symptoms:
        symptom_lower = symptom.lower()
        
        # Check for exact matches
        for key, specialists in symptom_to_specialty.items():
            if key in symptom_lower or symptom_lower in key:
                for specialist in specialists:
                    if specialist in recommended_specialists:
                        recommended_specialists[specialist] += 1
                    else:
                        recommended_specialists[specialist] = 1
    
    # Sort specialists by relevance (number of matching symptoms)
    sorted_specialists = sorted(
        recommended_specialists.items(), 
        key=lambda x: x[1], 
        reverse=True
    )
    
    # Return top 3 specialists with descriptions
    specialist_descriptions = {
        "Primary Care Physician": "For general health concerns and initial evaluation",
        "Neurologist": "Specializes in disorders of the brain and nervous system",
        "Cardiologist": "Specializes in heart conditions",
        "Pulmonologist": "Specializes in lung and respiratory conditions",
        "Gastroenterologist": "Specializes in digestive system disorders",
        "Dermatologist": "Specializes in skin conditions",
        "Rheumatologist": "Specializes in autoimmune and inflammatory conditions",
        "Orthopedic Surgeon": "Specializes in bone and joint conditions",
        "Otolaryngologist": "Specializes in ear, nose, and throat conditions",
        "Allergist": "Specializes in allergies and immune system disorders",
        "Endocrinologist": "Specializes in hormone-related conditions",
        "Infectious Disease Specialist": "Specializes in infections and related conditions",
        "Emergency Medicine": "For urgent and emergency medical conditions",
        "Psychiatrist": "Specializes in mental health conditions with medication management",
        "Psychologist": "Specializes in mental health therapy and counseling",
        "Ophthalmologist": "Specializes in eye diseases and conditions",
        "Urologist": "Specializes in urinary tract and male reproductive system",
        "Nephrologist": "Specializes in kidney diseases",
        "Colorectal Surgeon": "Specializes in conditions affecting the colon and rectum",
        "Audiologist": "Specializes in hearing disorders",
        "Sleep Specialist": "Specializes in sleep disorders and sleep medicine",
        "Geriatrician": "Specializes in healthcare for older adults",
        "Physical Therapist": "Specializes in physical rehabilitation and pain management"
    }
    
    result = []
    for specialist, count in sorted_specialists[:3]:
        result.append({
            "name": specialist,
            "description": specialist_descriptions.get(specialist, "Medical specialist"),
            "relevance_score": count
        })
    
    return result

def generate_assessment_cache_key(age, biological_sex, symptoms, symptom_details=None):
    """Generate a cache key for assessment results"""
    # Sort symptoms to ensure consistent key generation
    sorted_symptoms = sorted(symptoms)
    
    # Create a base key with essential parameters
    key_parts = [
        f"age:{age}",
        f"sex:{biological_sex}",
        f"symptoms:{','.join(sorted_symptoms)}"
    ]
    
    # Add symptom details if available
    if symptom_details:
        for k, v in sorted(symptom_details.items()):
            if isinstance(v, list):
                v = ','.join(sorted(v))
            key_parts.append(f"{k}:{v}")
    
    # Join all parts and create a hash
    key_string = "|".join(key_parts)
    return f"assessment:{hashlib.md5(key_string.encode()).hexdigest()}"
