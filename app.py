from flask import Flask, render_template, request, jsonify, send_file
from youtube_transcript_api import YouTubeTranscriptApi
import re
import os
import json
import google.generativeai as genai
from datetime import datetime
import math
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import io
import traceback
# ### FIX: This import is crucial for preventing errors from special characters
from xml.sax.saxutils import escape
import requests  # Added for alternative AI services
import random
from typing import Dict, List, Any


# Configure Gemini API (keep your original setup)
# IMPORTANT: For security, it's better to use an environment variable
# like os.environ.get("GEMINI_API_KEY") instead of pasting your key here.
genai.configure(api_key="") # <-- PASTE YOUR API KEY HERE

app = Flask(__name__)

# ### NEW: Alternative AI provider for PDF generation only
GROQ_API_KEY = os.environ.get("")  # Get free key from console.groq.com

# --- Helper Functions (KEEPING YOUR ORIGINAL LOGIC) ---

def extract_video_id(url):
    """Extract video ID from various YouTube URL formats"""
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None

def chunk_transcript(transcript, chunk_size=7000):
    """Split transcript into manageable chunks for processing"""
    words = transcript.split()
    chunks = []
    current_chunk = []
    current_length = 0
    for word in words:
        current_chunk.append(word)
        current_length += len(word) + 1
        if current_length >= chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk, current_length = [], 0
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    return chunks

def advanced_gemini_analysis(transcript):
    """Generate comprehensive analysis using Gemini API with multiple passes"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        chunks = chunk_transcript(transcript)
        all_analyses = []
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)}...")
            prompt = f"""
            Analyze this video transcript segment for a mind map. Return a JSON object with "main_theme" and "key_concepts".
            {{
                "main_theme": "Overall theme of this segment",
                "key_concepts": [
                    {{"concept": "Concept Name", "importance": 7, "description": "Details here",
                     "subconcepts": [{{"name": "Sub-concept", "details": "Sub-details"}}] }}
                ],
                "practical_applications": ["A practical takeaway"],
                "key_quotes": ["An important quote"]
            }}
            Transcript: {chunk}
            """
            try:
                response = model.generate_content(prompt)
                response_text = response.text.strip()
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    analysis = json.loads(json_str)
                    all_analyses.append(analysis)
            except Exception as e:
                print(f"Skipping a chunk due to processing error: {e}")
                continue
        return merge_analyses(all_analyses)
    except Exception as e:
        raise Exception(f"Gemini API error: {str(e)}")

def merge_analyses(analyses):
    """Merge multiple analysis chunks into a comprehensive structure"""
    if not analyses:
        return create_default_analysis("No content could be analyzed.")
    merged = {"main_theme": "Comprehensive Video Analysis", "key_concepts": [], "practical_applications": [], "key_quotes": []}
    concept_names = set()
    for analysis in analyses:
        if isinstance(analysis, dict):
            for concept in analysis.get("key_concepts", []):
                if isinstance(concept, dict) and concept.get("concept"):
                    if concept["concept"] not in concept_names:
                        concept_names.add(concept["concept"])
                        merged["key_concepts"].append(concept)
            for key in ["practical_applications", "key_quotes"]:
                merged[key].extend(analysis.get(key, []))
    if not merged["key_concepts"]:
        return create_default_analysis("Analysis failed to identify key concepts.")
    return merged

def create_default_analysis(message="Analysis Failed"):
    """Create a default analysis structure when parsing fails"""
    return {
        "main_theme": message,
        "key_concepts": [{"concept": "Error", "description": "Could not generate content from the video transcript."}],
        "practical_applications": [], "key_quotes": []
    }

def generate_3d_mind_map_data(analysis):
    """Convert analysis into 3D mind map data structure"""
    nodes, links = [], []
    if not analysis or not analysis.get("key_concepts"):
        analysis = create_default_analysis()

    center_node = {"id": "center", "name": analysis.get("main_theme", "Main Topic"), "type": "center", "size": 25, "color": "#ff6b6b", "x": 0, "y": 0, "z": 0, "description": "Central theme of the video"}
    nodes.append(center_node)
    
    concepts = analysis.get("key_concepts", [])
    angle_step = 2 * math.pi / len(concepts) if concepts else 0
    radius = 150
    for i, concept in enumerate(concepts):
        if not isinstance(concept, dict) or not concept.get("concept"): continue
        angle = i * angle_step
        concept_node = {"id": f"concept_{i}", "name": concept["concept"][:30], "type": "concept", "size": 15, "color": get_concept_color(i), "x": radius * math.cos(angle), "y": radius * math.sin(angle), "z": (i % 3 - 1) * 50, "description": concept.get("description", "")}
        nodes.append(concept_node)
        links.append({"source": "center", "target": f"concept_{i}"})
        sub_radius = radius + 80
        for j, subconcept in enumerate(concept.get("subconcepts", [])[:5]): # Limit subconcepts
            if not isinstance(subconcept, dict) or not subconcept.get("name"): continue
            sub_angle = angle + (j - len(concept.get("subconcepts", []))/2) * 0.1
            sub_node = {"id": f"sub_{i}_{j}", "name": subconcept["name"][:25], "type": "subconcept", "size": 6, "color": lighten_color(get_concept_color(i)), "x": sub_radius * math.cos(sub_angle), "y": sub_radius * math.sin(sub_angle), "z": concept_node["z"] + (j % 2 - 0.5) * 30, "description": subconcept.get("details", "")}
            nodes.append(sub_node)
            links.append({"source": f"concept_{i}", "target": f"sub_{i}_{j}"})
    return {"nodes": nodes, "links": links}

def get_concept_color(index):
    colors_list = ["#4ecdc4", "#45b7d1", "#96ceb4", "#ffeaa7", "#dda0dd", "#f7dc6f", "#bb8fce", "#85c1e9"]
    return colors_list[index % len(colors_list)]

def lighten_color(color):
    color = color.lstrip('#')
    rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
    light_rgb = tuple(min(255, c + 40) for c in rgb)
    return '#%02x%02x%02x' % light_rgb


# ===============================================================
# ### PDF GENERATION WITH ALTERNATIVE AI (ONLY CHANGE HERE)
# ===============================================================
def generate_comprehensive_notes_with_groq(analysis, transcript_text):
    """
    Generate comprehensive, tutorial-style notes using Groq API
    """
    try:
        if not GROQ_API_KEY:
            return None
            
        print("Generating comprehensive notes with Groq...")
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Create a much more detailed prompt for comprehensive notes
        comprehensive_prompt = f"""
        You are an expert educational content creator. Based on the video analysis and transcript provided, create comprehensive, tutorial-style study notes that are so detailed and well-explained that someone could learn everything without watching the video.

        REQUIREMENTS:
        1. Write in a conversational, engaging tone like a skilled teacher
        2. Explain concepts step-by-step with WHY behind each step
        3. Include practical examples and analogies
        4. Add context and background information
        5. Anticipate and answer potential student questions
        6. Use markdown formatting with proper headings
        7. Make it comprehensive - aim for 2000+ words
        8. Include troubleshooting tips and best practices

        STRUCTURE YOUR RESPONSE EXACTLY LIKE THIS:

        # [Topic Title] - Complete Guide

        ## 🎯 What You'll Learn
        [Clear learning objectives]

        ## 📚 Background & Context  
        [Explain the bigger picture, why this matters, industry context]

        ## 🔧 Prerequisites & Setup
        [What you need to know beforehand, setup requirements]

        ## 📖 Core Concepts Explained

        ### [Concept 1 Name]
        **What it is:** [Simple definition]
        **Why it matters:** [Importance and use cases]
        **How it works:** [Detailed step-by-step explanation]
        **Real-world example:** [Practical scenario]
        **Common mistakes to avoid:** [Pitfalls and solutions]

        [Repeat for each major concept]

        ## 🛠️ Step-by-Step Implementation
        [Detailed walkthrough of the process shown in video]

        ## ⚡ Pro Tips & Best Practices
        [Advanced insights and optimization techniques]

        ## 🚨 Troubleshooting Guide
        [Common issues and their solutions]

        ## 🎓 Practice Exercises
        [Suggested activities to reinforce learning]

        ## 🔗 Next Steps & Further Learning
        [What to explore next, related topics]

        ## ❓ Frequently Asked Questions
        [Anticipate and answer common questions]

        VIDEO ANALYSIS DATA:
        {json.dumps(analysis, indent=2)}

        TRANSCRIPT EXCERPT (for context):
        {transcript_text[:3000]}...

        Remember: Write as if you're explaining to a curious student who wants to truly understand, not just memorize. Use analogies, examples, and clear explanations for technical terms.
        """
        
        data = {
            "messages": [{"role": "user", "content": comprehensive_prompt}],
            "model": "mixtral-8x7b-32768",
            "temperature": 0.7,  # Higher temperature for more creative, engaging content
            "max_tokens": 4000   # Allow for longer, more detailed responses
        }
        
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                               headers=headers, json=data, timeout=60)  # Longer timeout for detailed response
        
        if response.status_code == 200:
            result = response.json()
            detailed_notes = result['choices'][0]['message']['content']
            print("SUCCESS: Generated comprehensive notes with Groq!")
            return detailed_notes
        else:
            print(f"Groq API failed with status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error with Groq comprehensive notes: {e}")
        return None

def generate_enhanced_fallback_notes(analysis, transcript_text):
    """
    Generate detailed fallback notes when AI services are unavailable
    """
    main_theme = analysis.get('main_theme', 'Video Analysis')
    
    notes = f"""# {main_theme} - Complete Study Guide

## 🎯 Learning Objectives
By the end of this guide, you will have a comprehensive understanding of all the key concepts, practical applications, and implementation details covered in this video content.

## 📚 Executive Summary
This video covers {len(analysis.get('key_concepts', []))} major concepts that are essential for understanding {main_theme.lower()}. The content provides both theoretical knowledge and practical implementation guidance.

## 🔧 Key Concepts Deep Dive

"""
    
    # Enhanced concept explanations
    for i, concept in enumerate(analysis.get('key_concepts', []), 1):
        concept_name = concept.get('concept', f'Concept {i}')
        description = concept.get('description', 'No description available')
        importance = concept.get('importance', 5)
        
        notes += f"""### {i}. {concept_name}

**⭐ Importance Level:** {importance}/10

**📝 What it is:**
{description}

**🎯 Why it matters:**
This concept is crucial because it {'forms the foundation' if importance >= 8 else 'provides important functionality' if importance >= 6 else 'adds valuable features'} for the overall implementation. Understanding this will help you {'master the core principles' if importance >= 8 else 'implement effectively' if importance >= 6 else 'use advanced features'}.

**🔍 Key Details:**
"""
        
        # Add subconcepts if available
        subconcepts = concept.get('subconcepts', [])
        if subconcepts:
            notes += f"This concept includes {len(subconcepts)} important sub-areas:\n"
            for j, sub in enumerate(subconcepts, 1):
                if isinstance(sub, dict):
                    sub_name = sub.get('name', f'Sub-concept {j}')
                    sub_details = sub.get('details', 'Details not available')
                    notes += f"   • **{sub_name}:** {sub_details}\n"
        else:
            notes += "- Core implementation details are covered in the video demonstration\n"
            notes += "- Practical examples show real-world application\n"
            notes += "- Best practices are highlighted throughout\n"
        
        notes += f"""
**💡 Practical Application:**
This concept is typically used when you need to {'implement core functionality' if importance >= 7 else 'add specific features' if importance >= 5 else 'enhance your implementation'}. You'll encounter this in real-world scenarios involving {'production systems' if importance >= 8 else 'development projects' if importance >= 6 else 'learning exercises'}.

**⚠️ Common Pitfalls:**
- Make sure to understand the underlying principles before implementation
- Pay attention to configuration and setup requirements
- Test thoroughly in your specific environment

---

"""
    
    # Enhanced practical applications
    if analysis.get('practical_applications'):
        notes += """## 🛠️ Practical Applications & Implementation

The video demonstrates several real-world applications:

"""
        for i, app in enumerate(analysis.get('practical_applications', []), 1):
            notes += f"""### Application {i}: {app}

**Implementation Approach:**
This application showcases how the concepts work together in practice. The step-by-step process involves careful setup, proper configuration, and systematic testing.

**Best Practices:**
- Follow the demonstrated sequence carefully
- Verify each step before proceeding
- Keep documentation of your configuration

"""
    
    # Enhanced quotes section
    if analysis.get('key_quotes'):
        notes += """## 💬 Key Insights & Quotes

These important statements from the video highlight critical points:

"""
        for i, quote in enumerate(analysis.get('key_quotes', []), 1):
            notes += f"""### Insight {i}
> "{quote}"

**Why this matters:** This quote emphasizes {'the importance of understanding fundamentals' if 'simple' in quote.lower() or 'basic' in quote.lower() else 'practical implementation considerations' if 'run' in quote.lower() or 'code' in quote.lower() else 'key principles for success'}.

"""
    
    # Add comprehensive sections
    notes += f"""## 🚀 Getting Started Checklist

Before implementing what you've learned:

- [ ] Review all key concepts and ensure understanding
- [ ] Set up your development environment properly  
- [ ] Have all required tools and dependencies ready
- [ ] Plan your implementation approach
- [ ] Prepare for potential troubleshooting

## 🎓 Study Tips

**For Maximum Retention:**
1. **Active Learning:** Don't just read - try implementing the concepts
2. **Practice Regularly:** Repetition helps solidify understanding
3. **Ask Questions:** Research areas that aren't completely clear
4. **Document Progress:** Keep notes on your implementation journey

**Common Study Mistakes to Avoid:**
- Rushing through complex concepts without full understanding
- Skipping hands-on practice
- Not testing in your own environment
- Ignoring error handling and edge cases

## 🔗 Next Steps for Continued Learning

**Immediate Actions:**
1. Review this guide thoroughly
2. Set up your practice environment
3. Implement the demonstrated concepts
4. Test with your own examples

**Advanced Topics to Explore:**
- Performance optimization techniques
- Error handling best practices
- Security considerations
- Scalability planning

## ❓ Frequently Asked Questions

**Q: What if I encounter errors during implementation?**
A: Errors are normal and expected. Review the troubleshooting section, check your setup, and ensure all prerequisites are met. The video likely shows common solutions.

**Q: How long should I spend practicing these concepts?**
A: Plan to spend focused time on each concept until you can implement it confidently without referring back to notes.

**Q: What's the best way to remember all these details?**
A: Active implementation is key. Build your own examples and variations to reinforce the learning.

---

## 📊 Summary Statistics

- **Total Concepts Covered:** {len(analysis.get('key_concepts', []))}
- **Practical Applications:** {len(analysis.get('practical_applications', []))}
- **Key Insights:** {len(analysis.get('key_quotes', []))}
- **Estimated Study Time:** {max(30, len(analysis.get('key_concepts', [])) * 15)} minutes for thorough review

*Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*

---

**💡 Remember:** The best way to learn is by doing. Use this guide as your roadmap, but make sure to implement and practice what you've learned!
"""
    
    return notes
def generate_pdf_from_markdown(markdown_text):
    """
    Safely converts markdown-like text from the AI into a list of
    ReportLab 'Flowables' (content blocks for the PDF).
    """
    story = []
    styles = getSampleStyleSheet()
    
    # Define custom styles for a clean look
    h1_style = ParagraphStyle('H1', parent=styles['h1'], fontSize=18, spaceBefore=20, spaceAfter=10, textColor=colors.HexColor('#2c3e50'))
    h2_style = ParagraphStyle('H2', parent=styles['h2'], fontSize=14, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor('#34495e'))
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=6)
    list_style = ParagraphStyle('List', parent=body_style, leftIndent=18, spaceAfter=2)

    for line in markdown_text.split('\n'):
        line = line.strip()
        
        # ### CRITICAL FIX: Escape special XML characters like '<' or '&'
        # This prevents ReportLab from crashing on weird AI output.
        safe_line = escape(line)

        if not safe_line:
            continue
            
        # Handle different markdown elements safely
        if line.startswith('# '):
            story.append(Paragraph(safe_line.replace('# ', ''), h1_style))
        elif line.startswith('## '):
            story.append(Paragraph(safe_line.replace('## ', ''), h2_style))
        elif line.startswith('* ') or line.startswith('- '):
            # ReportLab understands the '•' character for bullet points
            content = f"• {safe_line[2:]}"
            story.append(Paragraph(content, list_style))
        elif re.match(r'^\d+\.\s', line):
            story.append(Paragraph(safe_line, list_style))
        else:
            # Replace markdown bold with HTML bold, which ReportLab understands
            safe_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', safe_line)
            story.append(Paragraph(safe_line, body_style))
            
    return story

def generate_simple_notes_fallback(analysis):
    """Generate notes without using any AI (fallback method)"""
    notes = f"""# Study Notes: {analysis.get('main_theme', 'Video Analysis')}

## Overview
This document contains key concepts and insights extracted from the video analysis.

## Key Concepts

"""
    
    for i, concept in enumerate(analysis.get('key_concepts', []), 1):
        notes += f"**{i}. {concept.get('concept', 'Unknown')}**\n"
        notes += f"   - {concept.get('description', 'No description available')}\n"
        notes += f"   - Importance: {concept.get('importance', 5)}/10\n\n"
    
    if analysis.get('practical_applications'):
        notes += "## Practical Applications\n\n"
        for app in analysis.get('practical_applications', []):
            notes += f"* {app}\n"
        notes += "\n"
    
    if analysis.get('key_quotes'):
        notes += "## Key Quotes\n\n"
        for quote in analysis.get('key_quotes', []):
            notes += f'> "{quote}"\n\n'
    
    notes += f"\n---\n*Generated on: {datetime.now().strftime('%B %d, %Y')}*"
    return notes

def generate_detailed_notes(analysis, video_id, transcript_text=""):
    """
    Enhanced version that generates comprehensive, tutorial-style notes
    """
    try:
        
        detailed_notes_markdown = ""
        
        # Try comprehensive Groq generation first
        if GROQ_API_KEY:
            detailed_notes_markdown = generate_comprehensive_notes_with_groq(analysis, transcript_text)
        
        # If Groq failed or unavailable, use enhanced fallback
        if not detailed_notes_markdown:
            print("Using enhanced fallback method for comprehensive notes...")
            detailed_notes_markdown = generate_enhanced_fallback_notes(analysis, transcript_text)
        
        # Generate PDF with enhanced styling
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            rightMargin=0.75*inch, 
            leftMargin=0.75*inch, 
            topMargin=0.75*inch, 
            bottomMargin=0.75*inch
        )
        
        # Enhanced styles for professional look
        styles = getSampleStyleSheet()
        
        # Custom styles for better readability
        title_style = ParagraphStyle(
            'CustomTitle', 
            parent=styles['h1'], 
            fontSize=20, 
            alignment=1, 
            spaceAfter=30, 
            textColor=colors.HexColor('#2c3e50'),
            fontName='Helvetica-Bold'
        )
        
        story = []
        story.append(Paragraph(f"📚 {escape(analysis.get('main_theme', 'Video Analysis'))}", title_style))
        story.append(Paragraph("<i>Comprehensive Study Guide</i>", styles['Italic']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Use enhanced PDF generation
        story.extend(generate_enhanced_pdf_content(detailed_notes_markdown))
        
        # Professional footer
        story.append(Spacer(1, 0.5 * inch))
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | Comprehensive Study Notes", footer_style))

        doc.build(story)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        print("\n--- ERROR IN ENHANCED PDF GENERATION ---")
        traceback.print_exc()
        print("--- END OF ERROR ---\n")
        raise Exception(f"Failed to generate comprehensive PDF. Details: {str(e)}")
    
def generate_enhanced_pdf_content(markdown_text):
    """
    Enhanced PDF content generation with better styling and emoji support
    """
    story = []
    styles = getSampleStyleSheet()
    
    # Enhanced custom styles
    h1_style = ParagraphStyle(
        'CustomH1', 
        parent=styles['h1'], 
        fontSize=16, 
        spaceBefore=20, 
        spaceAfter=12, 
        textColor=colors.HexColor('#2980b9'),
        fontName='Helvetica-Bold'
    )
    
    h2_style = ParagraphStyle(
        'CustomH2', 
        parent=styles['h2'], 
        fontSize=14, 
        spaceBefore=15, 
        spaceAfter=8, 
        textColor=colors.HexColor('#27ae60'),
        fontName='Helvetica-Bold'
    )
    
    h3_style = ParagraphStyle(
        'CustomH3', 
        parent=styles['h3'], 
        fontSize=12, 
        spaceBefore=10, 
        spaceAfter=6, 
        textColor=colors.HexColor('#8e44ad'),
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody', 
        parent=styles['Normal'], 
        fontSize=10, 
        leading=14, 
        spaceAfter=8,
        alignment=0
    )
    
    quote_style = ParagraphStyle(
        'Quote', 
        parent=body_style, 
        leftIndent=20, 
        rightIndent=20, 
        textColor=colors.HexColor('#7f8c8d'), 
        fontName='Helvetica-Oblique',
        borderColor=colors.HexColor('#bdc3c7'),
        borderWidth=1,
        borderPadding=8
    )
    
    list_style = ParagraphStyle(
        'CustomList', 
        parent=body_style, 
        leftIndent=18, 
        spaceAfter=4
    )

    for line in markdown_text.split('\n'):
        line = line.strip()
        
        # Remove emoji characters that might cause issues (optional - you can keep them)
        # line = re.sub(r'[^\w\s\-\.\,\!\?\:\;\(\)\[\]\{\}\"\'\/\\\@\#\$\%\^\&\*\+\=\<\>\|]', '', line)
        
        safe_line = escape(line)

        if not safe_line:
            story.append(Spacer(1, 6))
            continue
            
        # Enhanced markdown parsing
        if line.startswith('# '):
            content = safe_line.replace('# ', '').replace('🎯', '').replace('📚', '').replace('🔧', '')
            story.append(Paragraph(content, h1_style))
        elif line.startswith('## '):
            content = safe_line.replace('## ', '').replace('🎯', '').replace('📚', '').replace('🔧', '').replace('🛠️', '').replace('⚡', '').replace('🚨', '').replace('🎓', '').replace('🔗', '').replace('❓', '')
            story.append(Paragraph(content, h2_style))
        elif line.startswith('### '):
            content = safe_line.replace('### ', '')
            story.append(Paragraph(content, h3_style))
        elif line.startswith('> '):
            content = safe_line.replace('> ', '')
            story.append(Paragraph(content, quote_style))
        elif line.startswith('* ') or line.startswith('- '):
            content = f"• {safe_line[2:]}"
            story.append(Paragraph(content, list_style))
        elif re.match(r'^\d+\.\s', line):
            story.append(Paragraph(safe_line, list_style))
        elif line.startswith('**') and line.endswith('**'):
            # Bold headers
            content = safe_line.replace('**', '')
            bold_style = ParagraphStyle('Bold', parent=body_style, fontName='Helvetica-Bold', spaceAfter=4)
            story.append(Paragraph(content, bold_style))
        else:
            # Enhanced text processing
            safe_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', safe_line)
            safe_line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', safe_line)
            if safe_line.strip():
                story.append(Paragraph(safe_line, body_style))
            
    return story

def generate_quiz_with_groq(analysis, transcript_text, quiz_type="mixed", num_questions=10):
    """
    Generate quiz questions using Groq API
    """
    try:
        if not GROQ_API_KEY:
            return None
            
        print(f"Generating {quiz_type} quiz with {num_questions} questions using Groq...")
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Create quiz-specific prompts based on type
        if quiz_type == "mcq":
            quiz_prompt = f"""
            Create {num_questions} multiple choice questions based on the video content. Return ONLY a valid JSON object with this exact structure:

            {{
                "quiz_type": "Multiple Choice Questions",
                "questions": [
                    {{
                        "id": 1,
                        "type": "mcq",
                        "question": "What is the main concept discussed?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_answer": 0,
                        "explanation": "Detailed explanation of why this is correct"
                    }}
                ]
            }}

            Requirements:
            - Make questions challenging but fair
            - Include plausible distractors
            - Provide clear explanations
            - Focus on key concepts from the video
            - Ensure correct_answer is the index (0-3) of the correct option
            """
        elif quiz_type == "true_false":
            quiz_prompt = f"""
            Create {num_questions} true/false questions based on the video content. Return ONLY a valid JSON object with this exact structure:

            {{
                "quiz_type": "True/False Questions", 
                "questions": [
                    {{
                        "id": 1,
                        "type": "true_false",
                        "question": "The main concept discussed is important for beginners.",
                        "correct_answer": true,
                        "explanation": "Explanation of why this statement is true or false"
                    }}
                ]
            }}

            Requirements:
            - Create clear, unambiguous statements
            - Mix true and false answers
            - Base questions on specific facts from the video
            - Provide detailed explanations
            """
        elif quiz_type == "fill_blank":
            quiz_prompt = f"""
            Create {num_questions} fill-in-the-blank questions based on the video content. Return ONLY a valid JSON object with this exact structure:

            {{
                "quiz_type": "Fill in the Blanks",
                "questions": [
                    {{
                        "id": 1,
                        "type": "fill_blank",
                        "question": "The main concept of _____ is essential for understanding _____.",
                        "correct_answers": ["programming", "software development"],
                        "explanation": "Explanation of the correct answers"
                    }}
                ]
            }}

            Requirements:
            - Use _____ to mark blanks
            - Provide all possible correct answers in the array
            - Make blanks focus on key terms/concepts
            - Keep answers concise (1-3 words typically)
            """
        else:  # mixed
            quiz_prompt = f"""
            Create a mixed quiz with {num_questions} questions ({num_questions//3} MCQ, {num_questions//3} True/False, remaining Fill-in-blanks) based on the video content. Return ONLY a valid JSON object with this exact structure:

            {{
                "quiz_type": "Mixed Quiz",
                "questions": [
                    {{
                        "id": 1,
                        "type": "mcq",
                        "question": "What is the main concept?",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": 0,
                        "explanation": "Explanation"
                    }},
                    {{
                        "id": 2,
                        "type": "true_false", 
                        "question": "Statement to evaluate",
                        "correct_answer": true,
                        "explanation": "Explanation"
                    }},
                    {{
                        "id": 3,
                        "type": "fill_blank",
                        "question": "Complete this: _____ is important for _____",
                        "correct_answers": ["concept", "learning"],
                        "explanation": "Explanation"
                    }}
                ]
            }}

            Requirements:
            - Mix question types evenly
            - Ensure all questions test important concepts
            - Provide clear explanations for all answers
            """

        full_prompt = f"""
        {quiz_prompt}

        VIDEO ANALYSIS:
        Main Theme: {analysis.get('main_theme', 'Unknown')}
        Key Concepts: {[concept.get('concept', '') for concept in analysis.get('key_concepts', [])]}
        
        TRANSCRIPT SAMPLE:
        {transcript_text[:2000]}...

        Remember: Return ONLY the JSON object, no additional text or formatting.
        """
        
        data = {
            "messages": [{"role": "user", "content": full_prompt}],
            "model": "mixtral-8x7b-32768",
            "temperature": 0.3,  # Lower temperature for more consistent quiz generation
            "max_tokens": 3000
        }
        
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                               headers=headers, json=data, timeout=45)
        
        if response.status_code == 200:
            result = response.json()
            quiz_content = result['choices'][0]['message']['content'].strip()
            
            # Extract JSON from response
            json_start = quiz_content.find('{')
            json_end = quiz_content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = quiz_content[json_start:json_end]
                quiz_data = json.loads(json_str)
                print(f"SUCCESS: Generated {len(quiz_data.get('questions', []))} quiz questions!")
                return quiz_data
            else:
                print("Failed to extract JSON from Groq response")
                return None
        else:
            print(f"Groq API failed with status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error generating quiz with Groq: {e}")
        return None
    
def generate_fallback_quiz(analysis, transcript_text, quiz_type="mixed", num_questions=10):
    """
    Generate quiz questions using fallback method when AI is unavailable
    """
    try:
        key_concepts = analysis.get('key_concepts', [])
        if not key_concepts:
            return create_default_quiz()
        
        questions = []
        question_id = 1
        
        # Determine question distribution
        if quiz_type == "mcq":
            mcq_count = num_questions
            tf_count = 0
            fb_count = 0
        elif quiz_type == "true_false":
            mcq_count = 0
            tf_count = num_questions
            fb_count = 0
        elif quiz_type == "fill_blank":
            mcq_count = 0
            tf_count = 0
            fb_count = num_questions
        else:  # mixed
            mcq_count = num_questions // 3
            tf_count = num_questions // 3
            fb_count = num_questions - mcq_count - tf_count
        
        # Generate MCQ questions
        for i in range(mcq_count):
            if i < len(key_concepts):
                concept = key_concepts[i]
                question = {
                    "id": question_id,
                    "type": "mcq",
                    "question": f"What is the main focus of '{concept.get('concept', 'this concept')}'?",
                    "options": [
                        concept.get('description', 'Primary description')[:50] + "...",
                        "Unrelated functionality",
                        "Basic setup only", 
                        "Advanced troubleshooting"
                    ],
                    "correct_answer": 0,
                    "explanation": f"The concept '{concept.get('concept', 'unknown')}' primarily focuses on: {concept.get('description', 'core functionality')}"
                }
                questions.append(question)
                question_id += 1
        
        # Generate True/False questions
        for i in range(tf_count):
            if i < len(key_concepts):
                concept = key_concepts[i]
                is_true = random.choice([True, False])
                if is_true:
                    question_text = f"The concept '{concept.get('concept', 'unknown')}' is covered in this video."
                    explanation = f"True. '{concept.get('concept', 'unknown')}' is indeed one of the key concepts discussed."
                else:
                    question_text = f"The concept '{concept.get('concept', 'unknown')}' is only briefly mentioned without explanation."
                    explanation = f"False. '{concept.get('concept', 'unknown')}' is thoroughly explained as a key concept."
                
                question = {
                    "id": question_id,
                    "type": "true_false",
                    "question": question_text,
                    "correct_answer": is_true,
                    "explanation": explanation
                }
                questions.append(question)
                question_id += 1
        
        # Generate Fill-in-the-blank questions
        for i in range(fb_count):
            if i < len(key_concepts):
                concept = key_concepts[i]
                concept_name = concept.get('concept', 'unknown')
                question = {
                    "id": question_id,
                    "type": "fill_blank",
                    "question": f"The key concept of _____ is essential for understanding the main topic.",
                    "correct_answers": [concept_name.lower(), concept_name],
                    "explanation": f"The answer is '{concept_name}' - this is one of the main concepts covered in the video."
                }
                questions.append(question)
                question_id += 1
        
        return {
            "quiz_type": f"{quiz_type.replace('_', ' ').title()} Quiz",
            "questions": questions
        }
        
    except Exception as e:
        print(f"Error in fallback quiz generation: {e}")
        return create_default_quiz()

def create_default_quiz():
    """Create a default quiz when generation fails"""
    return {
        "quiz_type": "Sample Quiz",
        "questions": [
            {
                "id": 1,
                "type": "mcq",
                "question": "What should you do if quiz generation fails?",
                "options": ["Try again", "Give up", "Use default", "All of above"],
                "correct_answer": 0,
                "explanation": "The best approach is to try again, as the issue might be temporary."
            }
        ]
    }
# ===============================================================
# ### END OF CHANGES - REST IS YOUR ORIGINAL CODE
# ===============================================================

# --- Flask Routes (KEEPING YOUR ORIGINAL ROUTES) ---

@app.route('/')
def index():
    """Main route that serves the HTML page."""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_video():
    """Processes the YouTube URL to generate mind map data."""
    try:
        data = request.get_json()
        youtube_url = data.get('youtube_url', '')
        
        video_id = extract_video_id(youtube_url)
        if not video_id:
            return jsonify({"error": "Invalid YouTube URL format."}), 400
        
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join([item['text'] for item in transcript_list])
            if len(transcript_text) < 100:
                return jsonify({"error": "Transcript is too short or unavailable."}), 400
        except Exception as e:
            return jsonify({"error": f"Could not get transcript. The video may not have captions enabled. Error: {e}"}), 400
        
        analysis = advanced_gemini_analysis(transcript_text)
        mind_map_data = generate_3d_mind_map_data(analysis)
        
        return jsonify({
            "success": True,
            "mind_map_data": mind_map_data,
            "analysis": analysis,
            "video_id": video_id,
            "transcript_text": transcript_text[:5000]  # Store first 5000 chars for PDF generation
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500

@app.route('/download-notes', methods=['POST'])
def download_notes():
    """Generates and serves the PDF notes for download."""
    try:
        data = request.get_json()
        analysis = data.get('analysis', {})
        video_id = data.get('video_id', 'unknown')
        transcript_text = data.get('transcript_text', '')  # Get transcript for comprehensive notes

        if not analysis or not analysis.get('key_concepts'):
             return jsonify({"error": "Analysis data is missing or invalid."}), 400
        
        # Pass transcript to the enhanced PDF generation function
        pdf_buffer = generate_detailed_notes(analysis, video_id, transcript_text)
        
        safe_title = re.sub(r'[^\w\s-]', '', analysis.get('main_theme', 'Video-Notes')).strip()
        cleaned_title = re.sub(r'[-\s]+', '-', safe_title)
        filename = f"{cleaned_title}-Comprehensive-Study-Guide.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate comprehensive notes. Reason: {str(e)}"}), 500
@app.route('/generate-quiz', methods=['POST'])
def generate_quiz():
    """Generate quiz questions based on video analysis"""
    try:
        data = request.get_json()
        analysis = data.get('analysis', {})
        transcript_text = data.get('transcript_text', '')
        quiz_type = data.get('quiz_type', 'mixed')  # mcq, true_false, fill_blank, mixed
        num_questions = int(data.get('num_questions', 10))
        
        # Validate inputs
        if not analysis or not analysis.get('key_concepts'):
            return jsonify({"error": "Analysis data is required to generate quiz."}), 400
        
        if num_questions < 1 or num_questions > 20:
            return jsonify({"error": "Number of questions must be between 1 and 20."}), 400
        
        if quiz_type not in ['mcq', 'true_false', 'fill_blank', 'mixed']:
            return jsonify({"error": "Invalid quiz type."}), 400
        
        # Try to generate quiz with Groq first
        quiz_data = None
        if GROQ_API_KEY:
            quiz_data = generate_quiz_with_groq(analysis, transcript_text, quiz_type, num_questions)
        
        # Use fallback if Groq failed or unavailable
        if not quiz_data:
            print("Using fallback method for quiz generation...")
            quiz_data = generate_fallback_quiz(analysis, transcript_text, quiz_type, num_questions)
        
        if not quiz_data or not quiz_data.get('questions'):
            return jsonify({"error": "Failed to generate quiz questions."}), 500
        
        return jsonify({
            "success": True,
            "quiz": quiz_data,
            "total_questions": len(quiz_data.get('questions', [])),
            "quiz_type": quiz_type
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Quiz generation failed: {str(e)}"}), 500

@app.route('/quiz')
def quiz_page():
    """Render the quiz page"""
    return render_template('quiz.html')

if __name__ == '__main__':
    print("ROCKET Starting app...")
    if GROQ_API_KEY:
        print("SUCCESS: Groq API key found - will use for PDF generation")
    else:
        print("INFO: No Groq API key - will use fallback method for PDFs")
    print("INFO: Mind map generation still uses your original Gemini setup")
    app.run(debug=True, threaded=True)
