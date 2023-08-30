import requests

def get_unique_word(existing_words):
    num_errors = 0
    while True:
        response = requests.get("https://random-word-api.herokuapp.com/word?length=8")
        
        # Error handling: If the API call fails 50 times, break out of the loop
        if response.status_code != 200:
            print("API call failed.")
            num_errors += 1
            if num_errors > 50:
                break
            continue
        
        # The API returns a list with one word; extract it
        new_word = response.json()[0]
        
        # Check if the word is unique from the existing words
        if new_word not in existing_words:
            return new_word