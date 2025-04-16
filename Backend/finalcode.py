from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import re
from textblob import TextBlob
from itertools import chain

app = Flask(__name__)
CORS(app)  # Enable CORS

# ✅ Correct spelling
def correct_spelling(sentence):
    return str(TextBlob(sentence).correct()).strip()

# ✅ Fetch all place names from database (normalized)
def get_place_names(table_name, cursor):
    cursor.execute(f"SELECT LOWER(TRIM(name)) FROM {table_name}")  # Ensure lowercase & trimmed
    return set(row[0] for row in cursor.fetchall())

# ✅ Generate n-grams (1-word, 2-word, 3-word)
def generate_ngrams(words, n):
    return [" ".join(words[i:i+n]) for i in range(len(words)-n+1)]

# ✅ Custom tokenizer (No `punkt` or `TextBlob` needed)
def tokenize(sentence):
    return re.findall(r'\b\w+\b', sentence.lower())  # Extract words using regex

# ✅ Find places (Supports Multi-Word Names)
def find_place_names(sentence, place_data):
    words = tokenize(sentence)  # Use custom tokenizer
    ngrams = list(chain(generate_ngrams(words, 1), generate_ngrams(words, 2), generate_ngrams(words, 3)))  
    return list({place.title() for place in place_data if place in ngrams})  # Remove duplicates, capitalize

@app.route('/identify', methods=['POST'])
def identify_places():
    try:
        data = request.json
        sentence = correct_spelling(data.get("sentence", ""))  

        # ✅ Connect to database
        conn = sqlite3.connect('geospatialdata.db')
        cursor = conn.cursor()

        # ✅ Fetch all place names (normalized)
        country_names = get_place_names('Countries', cursor)
        state_names = get_place_names('States', cursor)
        city_names = get_place_names('Cities', cursor)

        # ✅ Identify correct places
        places = {
            "Countries": find_place_names(sentence, country_names),
            "States": find_place_names(sentence, state_names),
            "Cities": find_place_names(sentence, city_names)
        }

        conn.close()

        # ✅ Remove empty categories
        places = {k: v for k, v in places.items() if v}

        return jsonify({"places": places})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
