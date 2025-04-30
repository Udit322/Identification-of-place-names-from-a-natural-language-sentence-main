from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import re
from textblob import TextBlob
from itertools import chain
from difflib import get_close_matches

app = Flask(__name__)
CORS(app)  # Enable CORS

#  Correct spelling using TextBlob (not used in fuzzy matching currently)
def correct_spelling(sentence):
    return str(TextBlob(sentence).correct()).strip()

#  Fetch all place names from database (normalized)
def get_place_names(table_name, cursor):
    cursor.execute(f"SELECT LOWER(TRIM(name)) FROM {table_name}")  # Ensure lowercase & trimmed
    return set(row[0] for row in cursor.fetchall())

#  Generate n-grams (1-word, 2-word, 3-word)
def generate_ngrams(words, n):
    return [" ".join(words[i:i+n]) for i in range(len(words)-n+1)]

#  Custom tokenizer (No `punkt` or `TextBlob` needed)
def tokenize(sentence):
    return re.findall(r'\b\w+\b', sentence.lower())  # Extract words using regex

#  Fuzzy match fallback
def fuzzy_match_ngrams(ngrams, place_data, cutoff=0.60):
    matches = set()
    for gram in ngrams:
        close = get_close_matches(gram, place_data, n=1, cutoff=cutoff)
        if close:
            matches.add(close[0])
    return matches

#  Find places (Supports Multi-Word Names + Fuzzy Matching)
def find_place_names(sentence, place_data):
    words = tokenize(sentence)
    ngrams = list(chain(generate_ngrams(words, 1), generate_ngrams(words, 2), generate_ngrams(words, 3))) 
    print("WORDS:", words)
    print("NGRAMS:", ngrams)
    print("PLACE_DATA SAMPLE:", list(place_data)[:10])  # just to check data

    # First, try exact matches
    found = {place.title() for place in place_data if place in ngrams}

    # If no exact matches, use fuzzy matching
    if not found:
        fuzzy_found = fuzzy_match_ngrams(ngrams, place_data)
        found.update([place.title() for place in fuzzy_found])

    return list(found)

#  Route to identify place names
@app.route('/identify', methods=['POST'])
def identify_places():
    try:
        data = request.json
        sentence = data.get("sentence", "").strip().lower()

        #  Connect to database
        conn = sqlite3.connect('geospatialdata.db')
        cursor = conn.cursor()

        #  Fetch all place names (normalized)
        country_names = get_place_names('Countries', cursor)
        state_names = get_place_names('States', cursor)
        city_names = get_place_names('Cities', cursor)

        #  Identify correct places
        places = {
            "Countries": find_place_names(sentence, country_names),
            "States": find_place_names(sentence, state_names),
            "Cities": find_place_names(sentence, city_names)
        }

        conn.close()

        #  Remove empty categories
        places = {k: v for k, v in places.items() if v}

        return jsonify({"places": places})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
