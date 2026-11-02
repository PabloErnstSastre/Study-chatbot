# StudyBot

## Quick Start

1. **Navigate to the directory:**
   ```bash
   cd /path/to/study-chatbot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application** (it will prompt for an API key if not configured):
   > You will need a free Google Gemini API Key → [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
   ```bash
   python chatbot.py
   ```

---

## 4. What is StudyBot?

StudyBot is a terminal-based chatbot that acts as your personal academic organization assistant. It leverages Google Gemini AI to answer questions about:
- Study hour distribution across subjects
- Personalized weekly schedule generation
- Weekend free-time optimization
- Study techniques and productivity tips

---

## 5. Script Architecture

### Main Modules

| Class / Function | Responsibility |
| :--- | :--- |
| `StudentProfile` | Student data model (subjects, hours, preferences) with JSON serialization. |
| `ProfileSetup` | Interactive terminal UI to create or edit the user profile. |
| `StudyBot` | Connects to the Gemini API, manages chat history and the system prompt. |
| `ChatUI` | Main chat loop, visual rendering using Rich, and command handling. |
| `get_api_key()` | Retrieves the API key from environment variables, `.env` file, or user input. |
| `main()` | Entry point: orchestrates the complete execution flow. |

---

## 6. How the AI Works

### Smart System Prompt
Upon startup, the bot injects the student's entire profile into Gemini's system prompt:

```text
STUDENT PROFILE:
 Name: Ana
 Level: University
 Prioritize weekend leisure: Yes

SUBJECTS:
- Mathematics (importance: 5/5, difficulty: 4/5, credits: 6.0)
- History (importance: 3/5, difficulty: 2/5, credits: 4.5)
 ...

AVAILABLE HOURS:
- Monday: 3.0h
- Tuesday: 3.0h
 ...
- Saturday: 0.5h ← minimum based on leisure preference
- Sunday: 0.5h
```

This ensures every Gemini response is context-aware without requiring you to repeat your details.

### Hour Distribution Algorithm
The bot calculates each subject's weight using the formula:
$$\text{weight}_i = \text{importance}_i \times 0.6 + \text{difficulty}_i \times 0.4$$

Hours per subject are distributed proportionally:
$$\text{hours}_i = \frac{\text{weight}_i}{\sum \text{weights}} \times \text{total\_weekly\_hours}$$

### Leisure Mode (Free Weekends)
When `prioritize_leisure` is enabled, the system prompt instructs Gemini to:
1. Limit Saturday and Sunday to **0–1 hour maximum** (light review only).
2. Redistribute those hours across Monday to Friday.

---

## 7. Profile Persistence

The profile is automatically saved to `student_profile.json` in the working directory:

```json
{
 "nombre": "Ana",
 "nivel": "universidad",
 "asignaturas": [
   {"nombre": "Matemáticas", "importancia": 5, "dificultad": 4, "creditos": 6.0},
   {"nombre": "Historia", "importancia": 3, "dificultad": 2, "creditos": 4.5}
 ],
 "horas_por_dia": {
   "Lunes": 3.0, "Martes": 3.0, "Miércoles": 2.5,
   "Jueves": 3.0, "Viernes": 2.0, "Sábado": 0.5, "Domingo": 0.5
 },
 "priorizar_ocio": true
}
```

Relaunching the script automatically loads your saved profile, avoiding re-configuration.

---

## 8. Visual Interface (Rich)

The script uses the `Rich` library to provide an attractive CLI experience:
- Distinct borders and colors for user vs. bot messages.
- Tables for schedules and subjects with visual importance/difficulty progress bars.
- Animated loading spinner while Gemini processes requests.
- Rendered Markdown support in bot responses (tables, bold text, lists).

---

## 9. Available Chat Commands

| Command | Action |
| :--- | :--- |
| `/perfil` | Edit name, subjects, available hours, and preferences |
| `/horario` | Request a complete, optimized weekly schedule |
| `/resumen` | View a visual summary table of subjects and availability |
| `/reset` | Clear chat history (retains profile data) |
| `/ayuda` | Show the list of available commands |
| `/salir` | Exit the chatbot |

---

## 10. How to Run

### Prerequisites
- **Python 3.10+** installed → [Download Python](https://www.python.org/downloads/)
- **Free Google Gemini API Key** → [Get API Key](https://aistudio.google.com/app/apikey)

### Step 1 — Open terminal in project folder
```powershell
cd C:\Users\MSI\.gemini\antigravity\scratch\study-chatbot
```

### Step 2 — Create virtual environment *(Optional but recommended)*
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### Step 3 — Install dependencies
```powershell
pip install -r requirements.txt
```
> *Note: If skipped, the script will attempt to auto-install missing packages on first run.*

### Step 4 — Configure API Key *(Choose one option)*

* **Option A — Environment Variable (Recommended):**
  ```powershell
  $env:GEMINI_API_KEY = "your_api_key_here"
  ```
* **Option B — `.env` File:**
  Create a `.env` file in the project root:
  ```env
  GEMINI_API_KEY="your_api_key_here"
  ```
* **Option C — Interactive Prompt:**
  Run the script and enter the key when prompted.

### Step 5 — Run the Chatbot
```powershell
python chatbot.py
```

---

## 🏁 First-Run Workflow
1. The script detects no existing profile.
2. Prompts you to set your name and education level.
3. Input your subjects along with their importance and difficulty scores.
4. Set available study hours for each day of the week.
5. Specify whether to prioritize weekend leisure time.
6. Saves your profile and launches the chatbot with a customized welcome message.

---

## 💡 Example Queries You Can Ask
- *"How many hours should I dedicate to each subject this week?"*
- *"I have a Math exam in 3 days, how should I reorganize my schedule?"*
- *"Give me a crash course plan for exam week."*
- *"What study technique do you recommend for History?"*
- *"Generate a schedule for this week using Pomodoro blocks."*
- *"How should I adjust my weekend schedule if I have an outing on Saturday afternoon?"*
