import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def create_pdf1(filename):
    c = canvas.Canvas(filename, pagesize=letter)
    # Page 1
    c.drawString(100, 750, "Page 1 - Cover Page of NIRM03 Report")
    c.drawString(100, 730, "Author: Master's Student")
    c.showPage()
    
    # Page 2
    c.drawString(100, 750, "Page 2 - Abstract & Intro")
    c.drawString(100, 730, "This is the second page introduction.")
    c.showPage()
    
    # Page 3
    text_lines = [
        "MINISTRY OF SCIENCE AND HIGHER EDUCATION OF THE REPUBLIC OF KAZAKHSTAN",
        "Kazakh University of Technology and Business named after K. Kulazhanov",
        "Faculty of \"Engineering and Information Technologies\" Department of \"Information Technologies\"",
        "REPORT on scientific research work NIRM 03 EP 7M06136 - \"Information Systems\"",
        "Topic: \"Methods of Self-Learning Speech Recognition and Their Adaptation for the Kazakh Language\"",
        "Course: 1 Master's student: ___________________________________________",
        "Scientific supervisor: Kasekeyeva A.B., PhD, Assistant Professor __________ Grade: Date: \"___\" ____________ 2025",
        "Astana 2025",
        "",
        "CONTENTS",
        "1. Self-Supervised ASR Architectures and Models",
        "1.1. wav2vec 2.0: Foundational Self-Supervised Learning Framework",
        "1.2. HuBERT: Hidden-Unit BERT for Speech Representation",
        "1.3. Conformer Architecture for Speech Recognition",
        "1.4. OpenAI Whisper: Large-Scale Multilingual ASR",
        "1.5. GigaAM: Efficient Self-Supervised Learner",
        "2. Adapting Self-Learning Models to Low-Resource Languages",
        "2.1. Cross-Lingual Self-Supervised Pre-training",
        "2.2. Multilingual Training on Related Turkic Languages",
        "2.3. Data Augmentation and TTS Integration",
        "2.4. Fine-tuning Strategies for Kazakh ASR",
        "",
        "3. Kazakh Speech Corpora and Resources 3.1. Kazakh Speech Corpus (KSC) 3.2. KSC2: Industrial-Scale Open-Source Corpus 3.3. KazakhTTS and KazakhTTS2 Datasets 3.4. Mozilla Common Voice (Kazakh)",
        "",
        "4. Case Studies and Experimental Results",
        "4.1. Comparison of ASR Models on Kazakh Datasets",
        "4.2. Fine-tuning Wav2Vec2.0 and Whisper for Kazakh",
        "4.3. Multilingual Turkic ASR System by ISSAI",
        "4.4. Practical Implementation Guidelines",
        "",
        "REFERENCES",
        "",
        "1. Self-Supervised ASR Architectures and Models",
        "Modern speech recognition has undergone a significant transformation, shifting from fully-supervised training paradigms to self-supervised or \"self-learning\" methods. These approaches learn useful speech representations from unlabeled audio data, dramatically reducing the dependency on expensive manual transcriptions. This paradigm shift has proven particularly valuable for lowresource languages like Kazakh, where annotated speech data is scarce.",
        "",
        "- 1.1. wav2vec 2.0: Foundational Self-Supervised Learning Framework",
        "A landmark work in self-supervised speech representation learning is wav2vec 2.0, introduced by Baevski et al. (2020). This framework masks portions of the audio signal in the latent space and trains a model to predict the latent representations of the masked portions through a contrastive learning objective. The architecture consists of a convolutional feature encoder that processes raw audio waveforms, followed by a Transformer network that builds contextualized representations. The key innovation of wav2vec 2.0 lies in its ability to leverage vast amounts of unlabeled audio for pre-training, followed by fine-tuning on limited"
    ]
    
    y = 750
    for line in text_lines:
        c.drawString(50, y, line)
        y -= 15
        if y < 50:
            c.showPage()
            y = 750
            
    c.showPage()
    c.save()
    print(f"Created {filename}")

def create_pdf2(filename):
    c = canvas.Canvas(filename, pagesize=letter)
    # Pages 1 to 22: simple text
    for i in range(1, 23):
        c.drawString(100, 750, f"Page {i} of Consolidated Financial Statements")
        c.drawString(100, 730, "Consolidated statement information text placeholder.")
        c.showPage()
        
    # Page 23: The complex table
    c.drawString(50, 750, "CONSOLIDATED STATEMENT OF FINANCIAL POSITION AS OF SEPTEMBER 30, 2025")
    c.drawString(50, 735, "(in millions of Kazakhstani tenge, unless otherwise stated)")
    
    # Table headers
    c.drawString(50, 700, "Assets")
    c.drawString(380, 700, "2025")
    c.drawString(460, 700, "2024")
    
    # Draw horizontal line
    c.line(50, 690, 530, 690)
    
    # Rows
    rows = [
        ("Cash and cash equivalents", "124,500", "98,200"),
        ("Trade and other receivables", "45,800", "39,100"),
        ("Inventories", "67,200", "55,400"),
        ("Property, plant and equipment", "412,300", "380,500"),
        ("Intangible assets", "15,400", "12,900"),
        ("Total assets", "665,200", "586,100"),
    ]
    
    y = 670
    for label, val1, val2 in rows:
        c.drawString(50, y, label)
        c.drawString(380, y, val1)
        c.drawString(460, y, val2)
        y -= 20
        
    c.line(50, y+10, 530, y+10)
    
    c.drawString(50, y-10, "Equity and liabilities")
    c.drawString(380, y-10, "2025")
    c.drawString(460, y-10, "2024")
    
    c.line(50, y-20, 530, y-20)
    
    rows_liab = [
        ("Share capital", "100,000", "100,000"),
        ("Retained earnings", "245,600", "210,400"),
        ("Total equity", "345,600", "310,400"),
        ("Long-term loans", "210,000", "190,000"),
        ("Trade and other payables", "109,600", "85,700"),
        ("Total equity and liabilities", "665,200", "586,100")
    ]
    
    y = y - 40
    for label, val1, val2 in rows_liab:
        c.drawString(50, y, label)
        c.drawString(380, y, val1)
        c.drawString(460, y, val2)
        y -= 20
        
    c.line(50, y+10, 530, y+10)
    c.showPage()
    c.save()
    print(f"Created {filename}")

if __name__ == "__main__":
    create_pdf1("NIRM03_SelfLearning_ASR_Kazakh_Updated.pdf")
    create_pdf2("09_2025_Consolidated Financial statements_IFRS_RUS.pdf")
    # Also create the copy needed by Cell 9
    import shutil
    shutil.copy("09_2025_Consolidated Financial statements_IFRS_RUS.pdf", "09_2025_Consolidated Financial statements_IFRS_RUS (1)-pages.pdf")
    print("Copied to 09_2025_Consolidated Financial statements_IFRS_RUS (1)-pages.pdf")
