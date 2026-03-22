import os
import json
import requests
import time

# Configuration
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_IDS = ['7695772994', '8070930921']
QUESTION_FILE = 'science_tech.txt'
PROGRESS_FILE = 'progress.json'
QUESTIONS_PER_DAY = 30

def parse_questions(file_path):
    questions = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    i = 0
    while i < len(lines):
        # Look for a block that looks like a question
        if i + 5 < len(lines) and lines[i+5].startswith('Answer:'):
            q_text = lines[i]
            options = [lines[i+1][2:], lines[i+2][2:], lines[i+3][2:], lines[i+4][2:]]
            ans_letter = lines[i+5].split(':')[1].strip()
            ans_idx = ord(ans_letter) - ord('A')
            
            questions.append({
                'question': q_text,
                'options': options,
                'correct_option_id': ans_idx
            })
            i += 6
        else:
            i += 1
    return questions

def send_poll(chat_id, question_data, question_num):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPoll"
    q_text = f"{question_num}. {question_data['question']}"
    payload = {
        'chat_id': chat_id,
        'question': q_text[:300], # Telegram limit
        'options': json.dumps(question_data['options']),
        'is_anonymous': False,
        'type': 'quiz',
        'correct_option_id': question_data['correct_option_id']
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending poll to {chat_id}: {e}")
        return False

def main():
    if not TOKEN:
        print("Error: TELEGRAM_TOKEN not set.")
        return

    questions = parse_questions(QUESTION_FILE)
    total_questions = len(questions)
    print(f"Total questions found: {total_questions}")

    # Load progress
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r') as f:
                progress = json.load(f)
            print(f"Loaded progress: last_index = {progress.get('last_index', 0)}")
        except Exception as e:
            print(f"Error loading progress file: {e}. Starting from 0.")
            progress = {'last_index': 0}
    else:
        print("No progress file found. Starting from 0.")
        progress = {'last_index': 0}

    start_idx = progress.get('last_index', 0)
    
    if start_idx >= total_questions:
        print("All questions finished. Sending completion message.")
        for chat_id in CHAT_IDS:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          data={'chat_id': chat_id, 'text': "no question, we done"})
        return

    end_idx = min(start_idx + QUESTIONS_PER_DAY, total_questions)
    print(f"Sending questions from index {start_idx} to {end_idx - 1} (Question #{start_idx + 1} to #{end_idx})")
    
    for i in range(start_idx, end_idx):
        q = questions[i]
        success = True
        for chat_id in CHAT_IDS:
            if not send_poll(chat_id, q, i + 1):
                success = False
            time.sleep(1) # Avoid rate limits
        
        # Update progress ONLY if successfully sent to both (or attempted)
        progress['last_index'] = i + 1
        with open(PROGRESS_FILE, 'w') as f:
             json.dump(progress, f)

    print(f"Done! New last_index is {progress['last_index']}")

    # Final message if done
    if progress['last_index'] >= total_questions:
        for chat_id in CHAT_IDS:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          data={'chat_id': chat_id, 'text': "no question, we done"})

if __name__ == "__main__":
    main()
