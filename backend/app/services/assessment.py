import json
import os
import re
from difflib import SequenceMatcher
from datetime import datetime

class AssessmentService:
    """Service for handling symptom assessment logic with enhanced analysis capabilities"""
    
    def __init__(self):
        """Initialize the assessment service with medical data"""
        self.symptoms = self._load_json_data('symptoms.json')
        self.conditions = self._load_json_data('conditions.json')
        self.questions = self._load_json_data('questions.json')
        self.body_regions = self._load_json_data('body_regions.json')
        self.symptom_relationships = self._load_json_data('symptom_relationships.json')
        
        # Cache for frequently accessed data
        self._symptom_name_to_id_map = {s['name'].lower(): s['id'] for s in self.symptoms if 'name' in s and 'id' in s}
        self._symptom_id_to_obj_map = {s['id']: s for s in self.symptoms if 'id' in s}
        # Create a mapping of symptom names to question flows for faster lookup
        self._symptom_to_question_flow = {}
        for symptom_key, flow in self.questions.items():
            if 'symptom_name' in flow:
                self._symptom_to_question_flow[flow['symptom_name'].lower()] = symptom_key
        
        # Track last returned question to prevent repetition
        self._last_question = None
        # Track previously asked questions by text to prevent repetition
        self._asked_questions_texts = set()
        # Track previously asked questions by ID to prevent repetition
        self._asked_questions_ids = set()
    
    def _load_json_data(self, filename):
        """Load JSON data from the backend/data directory, regardless of working directory."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.normpath(os.path.join(base_dir, '..', 'data'))
        file_path = os.path.join(data_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        print(f"Warning: Could not find data file {file_path}")
        return {}

    # ... (rest of your class code remains unchanged)
    # All other methods (search_symptoms, get_symptom_by_name, etc.) stay as they are.

        
        query = query.lower()
        exact_matches = []
        contains_matches = []
        similar_matches = []
        synonym_matches = []
        
        # Normalize the query (remove punctuation, standardize spacing)
        normalized_query = re.sub(r'[^\w\s]', '', query).strip()
        query_words = set(normalized_query.split())
        
        for symptom in self.symptoms:
            symptom_name = symptom['name'].lower()
            normalized_name = re.sub(r'[^\w\s]', '', symptom_name).strip()
            symptom_words = set(normalized_name.split())
            
            # Check for exact match
            if normalized_query == normalized_name:
                exact_matches.append(symptom)
                continue
                
            # Check if symptom contains the query
            if normalized_query in normalized_name:
                contains_matches.append(symptom)
                continue
                
            # Check for synonym matches
            if 'synonyms' in symptom:
                for synonym in symptom['synonyms']:
                    normalized_synonym = re.sub(r'[^\w\s]', '', synonym.lower()).strip()
                    if normalized_query in normalized_synonym or normalized_synonym in normalized_query:
                        synonym_matches.append(symptom)
                        break
                if symptom in synonym_matches:
                    continue
            
            # Check for word overlap (partial matches)
            word_overlap = len(query_words.intersection(symptom_words))
            if word_overlap > 0:
                # Calculate similarity score based on word overlap and sequence matching
                symptom['_word_overlap'] = word_overlap / max(len(query_words), len(symptom_words))
                contains_matches.append(symptom)
                continue
            
            # Check for similar symptoms using fuzzy matching
            similarity = self._similarity_score(normalized_query, normalized_name)
            if similarity > 0.7:  # Threshold for better precision
                symptom['_similarity'] = similarity  # Store for sorting
                similar_matches.append(symptom)
        
        # Sort each category by relevance
        contains_matches.sort(key=lambda x: x.get('_word_overlap', 0), reverse=True)
        similar_matches.sort(key=lambda x: x.get('_similarity', 0), reverse=True)
        
        # Combine results with priority: exact > contains > synonyms > similar
        results = exact_matches + contains_matches + synonym_matches + similar_matches
        
        # Remove duplicates while preserving order
        unique_results = []
        seen_ids = set()
        for item in results:
            if item['id'] not in seen_ids:
                seen_ids.add(item['id'])
                # Remove temporary scores
                if '_similarity' in item:
                    del item['_similarity']
                if '_word_overlap' in item:
                    del item['_word_overlap']
                unique_results.append(item)
        
        return unique_results[:15]  # Return top 15 matches for more options
    
    def _similarity_score(self, a, b):
        """Calculate similarity between two strings with improved algorithm"""
        if not a or not b:
            return 0
            
        # Direct comparison
        direct_ratio = SequenceMatcher(None, a, b).ratio()
        
        # Word set comparison (order-independent)
        a_words = set(a.split())
        b_words = set(b.split())
        
        if not a_words or not b_words:
            return direct_ratio
            
        # Jaccard similarity for word sets
        intersection = len(a_words.intersection(b_words))
        union = len(a_words.union(b_words))
        jaccard = intersection / union if union > 0 else 0
        
        # Word prefix matching (for partial word matches)
        prefix_matches = 0
        for a_word in a_words:
            for b_word in b_words:
                # Check if one word is a prefix of the other (min 3 chars)
                min_length = min(len(a_word), len(b_word))
                if min_length >= 3:
                    prefix_length = min(min_length, 5)  # Check up to 5 chars
                    if a_word[:prefix_length] == b_word[:prefix_length]:
                        prefix_matches += 1
                        break
        
        prefix_score = prefix_matches / max(len(a_words), len(b_words)) if max(len(a_words), len(b_words)) > 0 else 0
        
        # Combine metrics with appropriate weights
        return (direct_ratio * 0.6) + (jaccard * 0.3) + (prefix_score * 0.1)
    
    def get_symptom_by_name(self, symptom_name):
        """Get symptom object by name with efficient lookup"""
        if not symptom_name:
            return None
            
        symptom_name_lower = symptom_name.lower()
        
        # Direct lookup from cache
        if symptom_name_lower in self._symptom_name_to_id_map:
            symptom_id = self._symptom_name_to_id_map[symptom_name_lower]
            return self._symptom_id_to_obj_map.get(symptom_id)
        
        # Fuzzy matching if direct lookup fails
        best_match = None
        best_score = 0.8  # Higher threshold for name matching
        
        for symptom in self.symptoms:
            score = self._similarity_score(symptom_name_lower, symptom['name'].lower())
            if score > best_score:
                best_score = score
                best_match = symptom
                
        return best_match
    
    def _find_matching_question_flow(self, symptom):
        """Find the best matching question flow for a symptom"""
        symptom_lower = symptom.lower()
        
        # Direct lookup by symptom name
        if symptom_lower in self._symptom_to_question_flow:
            flow_key = self._symptom_to_question_flow[symptom_lower]
            return flow_key, self.questions[flow_key]
        
        # Try to find a close match
        best_match = None
        best_score = 0.7  # Threshold for matching
        best_key = None
        
        for key, flow in self.questions.items():
            if 'symptom_name' in flow:
                flow_symptom = flow['symptom_name'].lower()
                score = self._similarity_score(symptom_lower, flow_symptom)
                if score > best_score:
                    best_score = score
                    best_match = flow
                    best_key = key
        
        return best_key, best_match
    
    def reset_question_tracking(self):
        """Reset the question tracking to start a new assessment"""
        self._last_question = None
        self._asked_questions_texts = set()
        self._asked_questions_ids = set()
    
    def mark_question_asked(self, question):
        """Mark a question as asked to prevent repetition"""
        if question:
            self._last_question = question
            if 'id' in question:
                self._asked_questions_ids.add(question['id'])
            if 'text' in question:
                self._asked_questions_texts.add(question['text'])
    
    def is_question_repeated(self, question):
        """Check if a question has already been asked"""
        if not question:
            return False
            
        # Check by ID
        if 'id' in question and question['id'] in self._asked_questions_ids:
            return True
            
        # Check by text
        if 'text' in question and question['text'] in self._asked_questions_texts:
            return True
            
        # Check against last question
        if self._last_question:
            if 'id' in question and 'id' in self._last_question and question['id'] == self._last_question['id']:
                return True
            if 'text' in question and 'text' in self._last_question and question['text'] == self._last_question['text']:
                return True
                
        return False
    
    def get_first_question(self, symptom):
        """Get the first question for a given symptom with improved matching"""
        # Try to find a matching question flow
        flow_key, flow = self._find_matching_question_flow(symptom)
        
        if flow and 'first_question' in flow:
            # Clone the question and customize it for this specific symptom
            question = dict(flow['first_question'])
            
            # Replace symptom name in question text if needed
            if 'symptom_name' in flow and flow['symptom_name'].lower() != symptom.lower():
                question['text'] = question['text'].replace(
                    flow['symptom_name'], 
                    symptom
                )
            
            # Store this as the last question to prevent repetition
            self.mark_question_asked(question)
            
            return question
        
        # Try to find the symptom in our database for fallback
        symptom_obj = self.get_symptom_by_name(symptom)
        
        # Check if we have body region information for this symptom
        body_region = None
        if symptom_obj and 'body_region' in symptom_obj:
            body_region = symptom_obj['body_region']
        
        # Create a customized default question based on symptom characteristics
        symptom_characteristics = self._get_symptom_characteristics(symptom)
        duration_options = self._get_duration_options(symptom_characteristics.get('typical_duration', 'acute'))
        
        default_question = {
            "id": "duration",
            "text": f"How long have you been experiencing {symptom}?",
            "options": duration_options
        }
        
        # Store this as the last question to prevent repetition
        self.mark_question_asked(default_question)
        
        return default_question
    
    def get_next_question(self, symptoms, previous_answers):
        """Determine the next question based on symptoms and previous answers with enhanced logic"""
        if not symptoms:
            return None
            
        main_symptom = symptoms[0] if isinstance(symptoms, list) else symptoms
        main_symptom_lower = main_symptom.lower()
        
        # Find the matching question flow
        flow_key, flow = self._find_matching_question_flow(main_symptom)
        
        # If we have a specific flow for this symptom, use it
        if flow and 'follow_up_questions' in flow:
            # Find the last answered question in this flow
            last_question_id = None
            last_answer = None
            
            # Sort previous answers by their question IDs to find the most recent one
            # that belongs to our flow
            for q_id in sorted(previous_answers.keys(), reverse=True):
                # Check if this question is part of our flow
                if q_id in flow['follow_up_questions']:
                    last_question_id = q_id
                    last_answer = previous_answers[q_id]
                    break
            
            # If we found a previous question in this flow
            if last_question_id:
                next_question_info = flow['follow_up_questions'][last_question_id]
                
                # Handle conditional branching
                if 'condition' in next_question_info:
                    condition = next_question_info['condition']
                    condition_met = False
                    
                    if 'answer' in condition:
                        # Single answer condition
                        condition_met = condition['answer'] == last_answer
                    elif 'answers' in condition:
                        # Multiple possible answers condition
                        condition_met = last_answer in condition['answers']
                    elif 'contains' in condition:
                        # Check if answer contains specific text
                        condition_met = isinstance(last_answer, str) and condition['contains'] in last_answer.lower()
                    elif 'not_contains' in condition:
                        # Check if answer does NOT contain specific text
                        condition_met = not (isinstance(last_answer, str) and condition['not_contains'] in last_answer.lower())
                    
                    if condition_met and 'next_question' in next_question_info:
                        next_question = next_question_info['next_question']
                        # Check if this is a repeated question
                        if self.is_question_repeated(next_question):
                            # Skip to another question or return None
                            return None
                        self.mark_question_asked(next_question)
                        return next_question
                elif 'next_question' in next_question_info:
                    # No condition, just return the next question
                    next_question = next_question_info['next_question']
                    # Check if this is a repeated question
                    if self.is_question_repeated(next_question):
                        # Skip to another question or return None
                        return None
                    self.mark_question_asked(next_question)
                    return next_question
            
            # If we haven't asked the first question yet, start with that
            if not any(q_id.startswith(flow_key) for q_id in previous_answers.keys()):
                first_question = flow.get('first_question')
                if not self.is_question_repeated(first_question):
                    self.mark_question_asked(first_question)
                    return first_question
        
        # If no specific flow or we've exhausted the flow, use the adaptive questioning approach
        
        # Determine which questions have been asked and what information we need
        has_duration = any(q.startswith('duration') for q in previous_answers.keys())
        has_severity = any(q.startswith('severity') for q in previous_answers.keys())
        has_pattern = any(q.startswith('pattern') for q in previous_answers.keys())
        has_triggers = any(q.startswith('trigger') for q in previous_answers.keys())
        has_additional_symptoms = any(q.startswith('additional_symptoms') for q in previous_answers.keys())
        has_impact = any(q.startswith('impact') for q in previous_answers.keys())
        has_relief = any(q.startswith('relief') for q in previous_answers.keys())
        has_worsening = any(q.startswith('worsening') for q in previous_answers.keys())
        
        # Get symptom characteristics to customize questions
        symptom_characteristics = self._get_symptom_characteristics(main_symptom)
        
        # Prioritize questions based on medical relevance and symptom characteristics
        
        # 1. Duration is usually the first question for any symptom
        if not has_duration:
            duration_options = self._get_duration_options(symptom_characteristics.get('typical_duration', 'acute'))
            question = {
                "id": "duration",
                "text": f"How long have you been experiencing {main_symptom}?",
                "options": duration_options
            }
            if not self.is_question_repeated(question):
                self.mark_question_asked(question)
                return question
        
        # 2. Severity is typically the second most important question
        if not has_severity:
            question = {
                "id": "severity",
                "text": f"On a scale from 1 to 10, how would you rate the severity of your {main_symptom}?",
                "options": ["1 (Very mild)", "2", "3", "4", "5 (Moderate)", "6", "7", "8", "9", "10 (Severe)"]
            }
            if not self.is_question_repeated(question):
                self.mark_question_asked(question)
                return question
        
        # 3. Pattern helps understand the nature of the symptom
        if not has_pattern:
            pattern_options = self._get_pattern_options(symptom_characteristics.get('type', 'general'))
            question = {
                "id": "pattern",
                "text": f"How would you describe the pattern of your {main_symptom}?",
                "options": pattern_options
            }
            if not self.is_question_repeated(question):
                self.mark_question_asked(question)
                return question
        
        # 4. For severe or persistent symptoms, ask about worsening
        severity_level = 0
        if has_severity:
            try:
                # Extract numeric part from severity answer
                severity_text = next(answer for key, answer in previous_answers.items() if key.startswith('severity'))
                severity_level = int(severity_text.split()[0]) if ' ' in severity_text else int(severity_text)
            except (ValueError, IndexError, StopIteration):
                severity_level = 5  # Default to moderate if parsing fails
                
        duration_answer = next((answer for key, answer in previous_answers.items() if key.startswith('duration')), '')
        is_persistent = any(term in duration_answer.lower() for term in ['week', 'month', 'year'])
        
        if (severity_level >= 7 or is_persistent) and not has_worsening:
            question = {
                "id": "worsening",
                "text": f"Has your {main_symptom} gotten worse recently?",
                "options": ["Yes, significantly worse", "Yes, somewhat worse", "No change", "It's actually improving"]
            }
            if not self.is_question_repeated(question):
                self.mark_question_asked(question)
                return question
        
        # 5. Ask about additional symptoms to help with diagnosis
        if not has_additional_symptoms:
            related_symptoms = self.get_related_symptoms(main_symptom)
            
            question = {
                "id": "additional_symptoms",
                "text": f"Are you experiencing any other symptoms along with {main_symptom}?",
                "options": related_symptoms + ["None of these"],
                "multiple_select": True
            }
            if not self.is_question_repeated(question):
                self.mark_question_asked(question)
                return question
        
        # 6. Ask about triggers to understand potential causes
        if not has_triggers:
            # Customize trigger options based on symptom type
            trigger_options = self._get_relevant_triggers(main_symptom)
            
            question = {
                "id": "triggers",
                "text": f"Does anything seem to trigger or worsen your {main_symptom}?",
                "options": trigger_options,
                "multiple_select": True
            }
            if not self.is_question_repeated(question):
                self.mark_question_asked(question)
                return question
        
        # 7. Ask about impact on daily life
        if not has_impact:
            question = {
                "id": "impact",
                "text": f"How much is this {main_symptom} affecting your daily activities?",
                "options": [
                    "Not at all", 
                    "Slightly limiting", 
                    "Moderately limiting", 
                    "Severely limiting", 
                    "Completely unable to perform normal activities"
                ]
            }
            if not self.is_question_repeated(question):
                self.mark_question_asked(question)
                return question
        
        # 8. Ask about relief measures
        if not has_relief:
            # Customize relief options based on symptom type
            relief_options = self._get_relevant_relief_measures(main_symptom)
            
            question = {
                "id": "relief",
                "text": f"Have you tried anything that helps relieve your {main_symptom}?",
                "options": relief_options,
                "multiple_select": True
            }
            if not self.is_question_repeated(question):
                self.mark_question_asked(question)
                return question
        
        # If we've asked all standard questions, check for symptom-specific questions
        symptom_specific_question = self._get_symptom_specific_question(main_symptom, previous_answers)
        if symptom_specific_question and not self.is_question_repeated(symptom_specific_question):
            self.mark_question_asked(symptom_specific_question)
            return symptom_specific_question
        
        # No more questions
        self._last_question = None
        return None
    
    def get_related_symptoms(self, symptom):
        """Get symptoms commonly associated with the given symptom with improved relationship detection"""
        # Get the symptom object
        symptom_obj = self.get_symptom_by_name(symptom)
        symptom_id = symptom_obj['id'] if symptom_obj else None
        
        # First check if we have relationships defined in our database
        if self.symptom_relationships:
            # Direct lookup by symptom name
            for relationship in self.symptom_relationships:
                if relationship.get('primary_symptom', '').lower() == symptom.lower():
                    return relationship.get('related_symptoms', [])
            
            # Lookup by symptom ID if available
            if symptom_id:
                for relationship in self.symptom_relationships:
                    if relationship.get('primary_symptom_id') == symptom_id:
                        return relationship.get('related_symptoms', [])
        
        # Check for related symptoms based on conditions
        condition_based_symptoms = self._get_symptoms_from_conditions(symptom)
        if condition_based_symptoms:
            return condition_based_symptoms
        
        # Fallback to hardcoded associations
        common_associations = {
            "headache": ["Nausea", "Sensitivity to light", "Dizziness", "Fatigue", "Vision changes", "Neck pain"],
            "cough": ["Sore throat", "Runny nose", "Fever", "Shortness of breath", "Chest pain", "Wheezing"],
            "fever": ["Chills", "Sweating", "Headache", "Muscle aches", "Fatigue", "Loss of appetite"],
            "stomach pain": ["Nausea", "Vomiting", "Diarrhea", "Loss of appetite", "Bloating", "Constipation"],
            "abdominal pain": ["Nausea", "Vomiting", "Diarrhea", "Loss of appetite", "Bloating", "Constipation"],
            "chest pain": ["Shortness of breath", "Sweating", "Nausea", "Dizziness", "Pain in arm or jaw", "Heart palpitations"],
            "rash": ["Itching", "Swelling", "Redness", "Fever", "Pain", "Blisters"],
            "fatigue": ["Headache", "Muscle weakness", "Difficulty concentrating", "Sleep problems", "Sore throat", "Low mood"],
            "runny nose": ["Sneezing", "Congestion", "Sore throat", "Cough", "Watery eyes", "Itchy eyes"],
            "joint pain": ["Swelling", "Redness", "Stiffness", "Limited movement", "Warmth in the joint", "Morning stiffness"],
            "back pain": ["Stiffness", "Numbness", "Tingling", "Weakness", "Difficulty moving", "Pain radiating to legs"],
            "dizziness": ["Lightheadedness", "Vertigo", "Nausea", "Headache", "Balance problems", "Fainting"],
            "shortness of breath": ["Chest pain", "Cough", "Wheezing", "Fatigue", "Rapid breathing", "Blue lips or fingernails"],
            "nausea": ["Vomiting", "Loss of appetite", "Stomach pain", "Dizziness", "Headache", "Diarrhea"],
            "anxiety": ["Racing heart", "Sweating", "Trembling", "Difficulty concentrating", "Sleep problems", "Irritability"],
            "depression": ["Low mood", "Loss of interest", "Fatigue", "Sleep changes", "Appetite changes", "Difficulty concentrating"]
        }
        
        # Default list of common symptoms if no specific associations found
        default_symptoms = ["Fever", "Fatigue", "Nausea", "Dizziness", "Shortness of breath", "Headache"]
        
        # Find the closest match in our associations dictionary
        best_match = None
        best_score = 0.6  # Minimum threshold
        
        for key in common_associations:
            score = self._similarity_score(symptom.lower(), key)
            if score > best_score:
                best_score = score
                best_match = key
        
        # If we found a good match, return those associations
        if best_match:
            return common_associations[best_match]
        
        return default_symptoms
    
    def _get_symptoms_from_conditions(self, symptom):
        """Extract related symptoms based on conditions that feature the given symptom"""
        if not self.conditions:
            return []
            
        symptom_lower = symptom.lower()
        related_symptoms = set()
        
        # Find conditions that include this symptom
        relevant_conditions = []
        for condition in self.conditions:
            # Check primary symptoms
            primary_symptoms = condition.get('primary_symptoms', [])
            secondary_symptoms = condition.get('secondary_symptoms', [])
            all_symptoms = primary_symptoms + secondary_symptoms
            
            # Check if symptom is in this condition
            if any(s.lower() == symptom_lower or self._similarity_score(s.lower(), symptom_lower) > 0.8 for s in all_symptoms):
                relevant_conditions.append(condition)
                
            # Also check symptom relationships if available
            if 'symptom_relationships' in condition:
                for rel in condition['symptom_relationships']:
                    if rel.get('symptom', '').lower() == symptom_lower:
                        relevant_conditions.append(condition)
                        break
        
        # Extract related symptoms from these conditions
        for condition in relevant_conditions:
            primary_symptoms = condition.get('primary_symptoms', [])
            secondary_symptoms = condition.get('secondary_symptoms', [])
            
            # Add all symptoms except the original one
            for s in primary_symptoms + secondary_symptoms:
                if s.lower() != symptom_lower:
                    related_symptoms.add(s)
        
        # Convert to list and limit to top 8 most common
        if related_symptoms:
            return list(related_symptoms)[:8]
        
        return []
    
    def _get_symptom_characteristics(self, symptom):
        """Get characteristics of a symptom to customize questions"""
        # Default characteristics
        characteristics = {
            'type': 'general',
            'typical_duration': 'acute',
            'body_region': 'general',
            'severity_type': 'pain'
        }
        
        # Get the symptom object
        symptom_obj = self.get_symptom_by_name(symptom)
        
        if symptom_obj:
            # Update with actual data if available
            if 'body_region' in symptom_obj:
                characteristics['body_region'] = symptom_obj['body_region']
                
            # Infer characteristics from symptom name
            symptom_lower = symptom.lower()
            
            # Determine type
            if any(term in symptom_lower for term in ['pain', 'ache', 'sore', 'hurt']):
                characteristics['type'] = 'pain'
                characteristics['severity_type'] = 'pain'
            elif any(term in symptom_lower for term in ['rash', 'itch', 'bump', 'spot']):
                characteristics['type'] = 'skin'
                characteristics['severity_type'] = 'discomfort'
            elif any(term in symptom_lower for term in ['dizz', 'vertigo', 'lightheaded']):
                characteristics['type'] = 'neurological'
                characteristics['severity_type'] = 'intensity'
            elif any(term in symptom_lower for term in ['cough', 'breath', 'wheez']):
                characteristics['type'] = 'respiratory'
                characteristics['severity_type'] = 'frequency'
            elif any(term in symptom_lower for term in ['nausea', 'vomit', 'diarrhea', 'constipation']):
                characteristics['type'] = 'gastrointestinal'
                characteristics['severity_type'] = 'frequency'
            
            # Determine typical duration
            if any(term in symptom_lower for term in ['chronic', 'recurring', 'persistent']):
                characteristics['typical_duration'] = 'chronic'
        
        return characteristics
    
    def _get_duration_options(self, duration_type):
        """Get appropriate duration options based on symptom type"""
        if duration_type == 'chronic':
            return [
                "Less than 1 week", 
                "1-4 weeks", 
                "1-3 months", 
                "3-6 months", 
                "6-12 months", 
                "More than 1 year"
            ]
        else:  # acute
            return [
                "Less than 24 hours", 
                "1-3 days", 
                "4-7 days", 
                "1-2 weeks", 
                "2-4 weeks", 
                "1-3 months", 
                "More than 3 months"
            ]
    
    def _get_pattern_options(self, symptom_type):
        """Get appropriate pattern options based on symptom type"""
        common_options = [
            "Constant (always present)", 
            "Intermittent (comes and goes)", 
            "Worsening over time", 
            "Improving over time", 
            "Fluctuating (varies in intensity)"
        ]
        
        if symptom_type == 'pain':
            return common_options + ["Sharp and sudden", "Dull and persistent"]
        elif symptom_type == 'respiratory':
            return common_options + ["Worse when lying down", "Worse with exertion"]
        elif symptom_type == 'gastrointestinal':
            return common_options + ["Related to meals", "Worse on empty stomach"]
        elif symptom_type == 'skin':
            return common_options + ["Spreading to new areas", "Changing appearance"]
        else:
            return common_options + ["Only occurs under specific circumstances"]
    
    def _get_relevant_triggers(self, symptom):
        """Get relevant triggers based on symptom type"""
        # Common triggers for all symptoms
        common_triggers = ["Physical activity", "Stress", "Time of day", "Weather changes", "Nothing specific"]
        
        # Symptom-specific triggers
        specific_triggers = {
            "headache": ["Bright lights", "Loud noises", "Certain foods", "Alcohol", "Lack of sleep", "Screen time"],
            "cough": ["Cold air", "Talking", "Lying down", "Deep breathing", "Dust or allergens"],
            "stomach pain": ["Eating", "Specific foods", "Hunger", "Stress", "Alcohol"],
            "abdominal pain": ["Eating", "Specific foods", "Hunger", "Stress", "Alcohol"],
            "chest pain": ["Physical exertion", "Stress", "Eating", "Deep breathing", "Lying down"],
            "rash": ["Heat", "Certain foods", "Medications", "Contact with substances", "Stress"],
            "joint pain": ["Movement", "Weather changes", "Physical activity", "Rest", "Specific positions"],
            "back pain": ["Sitting", "Standing", "Bending", "Lifting", "Specific movements"],
            "dizziness": ["Standing up", "Moving head", "Specific positions", "Eating"],
            "shortness of breath": ["Exercise", "Lying down", "Exposure to allergens", "Cold air"],
            "fatigue": ["Physical activity", "Mental exertion", "Stress", "Poor sleep", "Time of day"],
            "anxiety": ["Social situations", "Specific thoughts", "Uncertainty", "Work/school stress"],
            "depression": ["Time of day", "Social situations", "Specific thoughts", "Anniversaries/holidays"]
        }
        
        # Find the best matching symptom
        best_match = None
        best_score = 0.6
        
        for key in specific_triggers:
            score = self._similarity_score(symptom.lower(), key)
            if score > best_score:
                best_score = score
                best_match = key
        
        # If we found a match, combine common and specific triggers
        if best_match:
            combined_triggers = list(set(common_triggers + specific_triggers[best_match]))
            return sorted(combined_triggers)
        
        return common_triggers
    
    def _get_relevant_relief_measures(self, symptom):
        """Get relevant relief measures based on symptom type"""
        # Common relief measures for all symptoms
        common_measures = ["Over-the-counter medication", "Rest", "Home remedies", "Prescription medication", "Nothing has helped"]
        
        # Symptom-specific relief measures
        specific_measures = {
            "headache": ["Pain relievers", "Dark room", "Cold compress", "Caffeine", "Sleep"],
            "cough": ["Cough medicine", "Warm liquids", "Honey", "Humidifier", "Throat lozenges"],
            "fever": ["Fever reducers", "Cool compress", "Staying hydrated", "Light clothing"],
            "stomach pain": ["Antacids", "Heating pad", "Avoiding certain foods", "Small meals", "Ginger tea"],
            "abdominal pain": ["Antacids", "Heating pad", "Avoiding certain foods", "Small meals", "Ginger tea"],
            "chest pain": ["Resting", "Pain medication", "Antacids", "Sitting upright"],
            "rash": ["Topical creams", "Cool compress", "Antihistamines", "Avoiding irritants", "Oatmeal bath"],
            "joint pain": ["Pain relievers", "Hot/cold therapy", "Gentle stretching", "Joint braces", "Elevation"],
            "back pain": ["Pain relievers", "Heat therapy", "Cold therapy", "Stretching", "Massage"],
            "dizziness": ["Sitting down", "Hydration", "Avoiding sudden movements", "Ginger"],
            "shortness of breath": ["Sitting upright", "Using a fan", "Pursed lip breathing", "Inhaler"],
            "fatigue": ["Short naps", "Caffeine", "Regular sleep schedule", "Gentle exercise"],
            "anxiety": ["Deep breathing", "Meditation", "Talking to someone", "Distraction techniques"],
            "depression": ["Exercise", "Socializing", "Therapy", "Light therapy", "Regular routine"]
        }
        
        # Find the best matching symptom
        best_match = None
        best_score = 0.6
        
        for key in specific_measures:
            score = self._similarity_score(symptom.lower(), key)
            if score > best_score:
                best_score = score
                best_match = key
        
        # If we found a match, combine common and specific measures
        if best_match:
            combined_measures = list(set(common_measures + specific_measures[best_match]))
            return sorted(combined_measures)
        
        return common_measures
    
    def _get_symptom_specific_question(self, symptom, previous_answers):
        """Get additional symptom-specific questions based on the symptom and previous answers"""
        symptom_lower = symptom.lower()
        
        # Headache-specific questions
        if "headache" in symptom_lower or "migraine" in symptom_lower:
            if "headache_location" not in previous_answers:
                return {
                    "id": "headache_location",
                    "text": "Where is your headache located?",
                    "options": ["Front of the head", "Back of the head", "One side only", "Both sides", "All over", "Behind the eyes"]
                }
            elif "headache_character" not in previous_answers:
                return {
                    "id": "headache_character",
                    "text": "How would you describe the pain?",
                    "options": ["Throbbing/pulsating", "Pressure/squeezing", "Sharp/stabbing", "Dull ache", "Burning"]
                }
            elif "headache_aura" not in previous_answers:
                return {
                    "id": "headache_aura",
                    "text": "Before your headache begins, do you experience any warning signs like visual changes, numbness, or speech difficulties?",
                    "options": ["Yes", "No", "Sometimes"]
                }
        
        # Chest pain specific questions
        elif "chest" in symptom_lower and ("pain" in symptom_lower or "discomfort" in symptom_lower):
            if "chest_pain_location" not in previous_answers:
                return {
                    "id": "chest_pain_location",
                    "text": "Where exactly in your chest do you feel the pain?",
                    "options": ["Center of chest", "Left side", "Right side", "Upper chest", "Lower chest", "All over chest"]
                }
            elif "chest_pain_radiation" not in previous_answers:
                return {
                    "id": "chest_pain_radiation",
                    "text": "Does the pain spread or radiate to other areas?",
                    "options": ["Left arm", "Right arm", "Jaw or neck", "Back", "Abdomen", "No radiation"]
                }
            elif "chest_pain_breathing" not in previous_answers:
                return {
                    "id": "chest_pain_breathing",
                    "text": "Does the pain change with breathing?",
                    "options": ["Worse with deep breath", "Better with deep breath", "No change with breathing"]
                }
        
        # Abdominal pain specific questions
        elif ("stomach" in symptom_lower or "abdominal" in symptom_lower or "belly" in symptom_lower) and "pain" in symptom_lower:
            if "abdominal_pain_location" not in previous_answers:
                return {
                    "id": "abdominal_pain_location",
                    "text": "Where in your abdomen is the pain located?",
                    "options": ["Upper abdomen", "Lower abdomen", "Right side", "Left side", "Around the navel", "All over abdomen"]
                }
            elif "abdominal_pain_meals" not in previous_answers:
                return {
                    "id": "abdominal_pain_meals",
                    "text": "How does eating affect your pain?",
                    "options": ["Pain improves after eating", "Pain worsens after eating", "No relation to eating", "Pain occurs mainly when hungry"]
                }
            elif "bowel_changes" not in previous_answers:
                return {
                    "id": "bowel_changes",
                    "text": "Have you noticed any changes in your bowel movements?",
                    "options": ["Diarrhea", "Constipation", "Alternating diarrhea and constipation", "Blood in stool", "No changes"]
                }
        
        # Cough specific questions
        elif "cough" in symptom_lower:
            if "cough_type" not in previous_answers:
                return {
                    "id": "cough_type",
                    "text": "How would you describe your cough?",
                    "options": ["Dry (no mucus)", "Wet/productive (with mucus)", "Both", "Barking"]
                }
            elif "cough_type" in previous_answers and previous_answers["cough_type"] in ["Wet/productive (with mucus)", "Both"] and "sputum_color" not in previous_answers:
                return {
                    "id": "sputum_color",
                    "text": "What color is the mucus/phlegm you cough up?",
                    "options": ["Clear/white", "Yellow", "Green", "Brown", "Pink or red (blood-tinged)"]
                }
            elif "cough_timing" not in previous_answers:
                return {
                    "id": "cough_timing",
                    "text": "When is your cough worst?",
                    "options": ["Morning", "Night", "After exercise", "After eating", "No specific pattern"]
                }
        
        # Joint pain specific questions
        elif "joint" in symptom_lower and "pain" in symptom_lower:
            if "joint_location" not in previous_answers:
                return {
                    "id": "joint_location",
                    "text": "Which joints are affected?",
                    "options": ["Knees", "Hips", "Ankles", "Shoulders", "Elbows", "Wrists", "Fingers", "Toes", "Spine", "Multiple joints"],
                    "multiple_select": True
                }
            elif "joint_swelling" not in previous_answers:
                return {
                    "id": "joint_swelling",
                    "text": "Do you have any swelling in the affected joint(s)?",
                    "options": ["Yes", "No", "Sometimes"]
                }
            elif "joint_morning_stiffness" not in previous_answers:
                return {
                    "id": "joint_morning_stiffness",
                    "text": "Do you experience stiffness in your joints when you wake up in the morning?",
                    "options": ["Yes, for less than 30 minutes", "Yes, for 30 minutes to an hour", "Yes, for more than an hour", "No morning stiffness"]
                }
        
        # Shortness of breath specific questions
        elif "breath" in symptom_lower or "breathing" in symptom_lower:
            if "breathing_position" not in previous_answers:
                return {
                    "id": "breathing_position",
                    "text": "Is your breathing difficulty affected by your body position?",
                    "options": ["Worse when lying down", "Better when sitting upright", "Not affected by position"]
                }
            elif "breathing_exertion" not in previous_answers:
                return {
                    "id": "breathing_exertion",
                    "text": "How much exertion causes you to become short of breath?",
                    "options": ["At rest", "Minimal activity (getting dressed)", "Light activity (walking)", "Moderate activity (climbing stairs)", "Heavy activity (running)"]
                }
        
        # No additional symptom-specific questions
        return None
