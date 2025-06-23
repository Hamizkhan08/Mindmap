

# 🧠 YouTube to 3D Mind Map Generator

This project is an AI-powered web application that takes a YouTube video URL, extracts its transcript, analyzes the content using **Google Gemini AI**, and generates an interactive **3D mind map** to visually represent the core ideas and concepts.
---
![Screenshot 2025-06-23 230441](https://github.com/user-attachments/assets/04e76195-c716-4031-9f7a-d4628df7e76a)
![Screenshot 2025-06-23 230626](https://github.com/user-attachments/assets/f08b1b4a-40e0-4940-8091-e17a439dae76)

---
## 🚀 Features

- 🎥 Extracts transcript from YouTube videos
- 🤖 Uses Gemini or Groq AI to analyze content
- 🗺 Generates 3D interactive mind maps using `three.js`
- 📄 Exports AI-generated notes as beautifully formatted PDFs
- 🧪 Quiz module for testing knowledge based on the video
- 🌐 Clean, responsive front-end interface (HTML + CSS)

---

## 🧰 Tech Stack

| Layer       | Technologies Used                                  |
|-------------|-----------------------------------------------------|
| **Frontend**| HTML, CSS, JavaScript, Three.js                     |
| **Backend** | Python, Flask                                       |
| **AI Models**| Google Gemini API, Groq API (fallback)            |
| **Other**   | youtube-transcript-api, ReportLab (PDF generation) |

---

## 🛠 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/mindmap-generator.git
cd mindmap-generator
````

### 2. Create Virtual Environment (Optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔐 API Configuration

Edit the `app.py` file:

1. Replace the Gemini API key:

```python
genai.configure(api_key="YOUR_GEMINI_API_KEY")
```

2. Set the Groq API key as an environment variable:

```bash
export GROQ_API_KEY="YOUR_GROQ_API_KEY"
```

---

## ▶️ Running the Application

```bash
python app.py
```

Then open your browser and navigate to:
📍 `http://127.0.0.1:5000/`

---

## 📂 Project Structure

```
Mindmap/
│
├── app.py                 # Flask backend logic
├── requirements.txt       # Python dependencies
├── index.html             # Main front-end UI
├── mindmap.html           # Manual mind map input
├── quiz.html              # Quiz generation interface
├── mindmap.png            # Example mind map output
├── templates/             # (if used for Flask rendering)
├── static/                # CSS/JS assets (optional)
└── README.md              # This file
```

---

## 📸 Screenshots
![Screenshot 2025-06-23 230455](https://github.com/user-attachments/assets/c2649311-00d4-4c9d-a62d-bcc5356a0839)
![Screenshot 2025-06-23 230606](https://github.com/user-attachments/assets/191aee00-3cb7-4068-a44e-9c4ebeed4f74)
![Screenshot 2025-06-23 230626](https://github.com/user-attachments/assets/2e4a7623-cf87-45d1-a366-62d05ffc5380)
![Screenshot 2025-06-23 230711](https://github.com/user-attachments/assets/d170caa4-24f9-4694-a00c-1f0002ebfd98)
![Screenshot 2025-06-23 230723](https://github.com/user-attachments/assets/3b4e6507-97eb-4624-889d-342c4ae9c32c)
![Screenshot 2025-06-23 230734](https://github.com/user-attachments/assets/2f4ef3cc-29e0-453d-8798-8ddf6a470c97)
![Screenshot 2025-06-23 230830](https://github.com/user-attachments/assets/94106491-a077-43f1-910e-f75954824135)

> ![Mindmap Preview](mindmap.png)

---

## 🧠 How It Works

1. User submits a YouTube video URL.
2. Transcript is fetched via `youtube-transcript-api`.
3. AI analyzes the transcript to extract:

   * Main theme
   * Key concepts and subconcepts
   * Practical takeaways
   * Memorable quotes
4. The results are visualized in a **3D Mind Map** and also compiled into PDF notes.
5. A quiz is generated based on the AI summary for self-evaluation.

---

## 🧪 Sample Use Cases

* Studying long YouTube lectures/tutorials
* Converting educational videos into visual notes
* Creating study materials and quizzes from video content

---

## 📌 To Do

* [ ] Improve error handling for YouTube parsing
* [ ] Add multi-language transcript support
* [ ] Support for video upload (not just YouTube)
* [ ] Save mind maps and quizzes to database

---

## 📄 License

MIT License

---

## 🙌 Acknowledgements

* [Google Generative AI](https://ai.google.dev/)
* [Groq AI](https://console.groq.com/)
* [YouTube Transcript API](https://pypi.org/project/youtube-transcript-api/)
* [Three.js](https://threejs.org/)
