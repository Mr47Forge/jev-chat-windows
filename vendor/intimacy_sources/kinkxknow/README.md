<div align="center">

# KINK X KNOW
### *An Interactive Exploration of Sacred Desires & Lifestyle Archetypes*

[![Live Application](https://img.shields.io/badge/Live_App-KinkXKnow-FF1493?style=for-the-badge&logo=vercel)](https://kinkxknow.vercel.app)
[![Tech Stack](https://img.shields.io/badge/Tech_Stack-HTML5_|_Tailwind_|_ES6-D4AF37?style=for-the-badge)](#-tech-stack--design-system)
[![License: MIT](https://img.shields.io/badge/License-MIT-002366.svg?style=for-the-badge)](LICENSE)

An immersive, privacy-focused web platform designed to facilitate self-discovery, boundary awareness, and educational exploration of power dynamics, BDSM archetypes, and interpersonal dynamics.

<br />

<table align="center">
    <thead>
        <tr>
            <th>Module</th>
            <th>Description</th>
            <th>Primary Feature</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><b>Kink Calculator</b></td>
            <td>24-Entry Archetype Assessment</td>
            <td>Weighted scoring over 11 BDSM roles</td>
        </tr>
        <tr>
            <td><b>Understanding Kinks</b></td>
            <td>Educational Knowledge Base</td>
            <td>Visual taxonomy & safety insights</td>
        </tr>
        <tr>
            <td><b>Past Results</b></td>
            <td>Session Archives</td>
            <td>Local reflection & preference logging</td>
        </tr>
    </tbody>
</table>

</div>

---

## Overview

**KinkXKnow** combines modern web design with structured psychometric modeling to help users explore their personal preferences, relationship dynamics, and safety protocols. Built around a dark, luxury-glassmorphism aesthetic (**Royal Dark, Gold Rich, and Neon Pink**), the application offers an inviting space for consensual self-exploration.

Unlike standard questionnaires, the core engine measures nuanced responses across **five core categories** to calculate real-time archetype resonance, ideal partner dynamics, and practical relationship guidance.

---

## Features & Architecture

### 1. Archetype Assessment Engine (`StyleExplorer`)
* **24-Entry Evaluation Matrix:** Assesses preferences across 5 distinct domains:
  * **Safety:** Safewords, vulnerability, scene check-ins, public dynamics, and aftercare.
  * **Structure:** Written contracts, feedback loops, 24/7 vs. scene dynamics, and autonomy.
  * **Control:** Tasking, degradation, collaring, financial dynamics, and ownership concepts.
  * **Physical:** Impact play, bondage, sensory deprivation, medical kink, and temperature play.
  * **Edge:** Edge boundaries, breath control, urophilia, blood play, and pain tolerance.
* **11-Archetype Resonance Scoring:** Dynamically evaluates candidate weight vectors for:
  > *Submissive, Brat, Little, Pet, Rope Bunny, Dominant, Nurturer, Master, Rigger, Caretaker, Disciplinarian*
* **Detailed Revelation Breakdown:** Displays primary archetype match, ideal dynamic pairing, tailored safety tips, and relative resonance percentages across secondary archetypes.
* **Confetti Celebration:** Integrated `canvas-confetti` trigger on assessment completion.

### 2. Educational & Exploration Hub
* **Curated Knowledge Base:** Highlighting foundational concepts including Bondage, Dominance & Submission, Foot Worship, and Consensual Humiliation.
* **Safety First Philosophy:** Promotes active consent, Risk-Aware Consensual Kink (RACK), and Safe, Sane, and Consensual (SSC) principles throughout the user experience.

### 3. Luxury Glassmorphism Interface
* Custom Tailwind styling using backdrop blurs (`backdrop-blur-md`), gold-neon text glows, and responsive cards.
* Pixel-perfect typography using *Cinzel Decorative*, *Playfair Display*, and *Space Grotesk*.

---

## How the Scoring Engine Works

The calculation engine evaluates candidate answers against a weighted matrix ($\mathbf{W}$) mapping user input values ($a_q \in [0, 10]$) to specific archetypes:

$$S_{\text{style}} = \frac{\sum_{q \in Q} (a_q \cdot w_{q, \text{style}})}{\sum_{q \in Q} (|w_{q, \text{style}}| \cdot 10)} \times 100$$

where $w_{q, \text{style}}$ represents the positive or negative weight assigned to question $q$ for a given archetype. This guarantees that resistance traits (e.g., high autonomy demand for submissive roles) accurately scale the resulting percentage output.

---

## Tech Stack & Design System

* **Frontend Framework:** Vanilla JS (ES6 Classes), HTML5
* **Styling & Design System:**
  * **Tailwind CSS** (Custom theme configuration)
  * Custom Glassmorphism UI Components
* **Fonts:** `Cinzel Decorative`, `Cinzel`, `Playfair Display`, `Space Grotesk`, `Montserrat`
* **Icons:** Google Material Symbols Outlined
* **Libraries:** `canvas-confetti`

---

## Running Locally

No complex node dependencies or bundlers required—just standard web technology.

```
1. Clone the repository:
   git clone [https://github.com/dkconnect/kinkxknow.git](https://github.com/dkconnect/kinkxknow.git)
   cd kinkxknow

2. Serve the application: Launch using any static web server (e.g., Python's HTTP server): python -m http.server 8000

3. Access in browser:
   Open http://localhost:8000 in your web browser.
```

## Repository Structure
```
.
├── index.html          # Main landing page & gateway menu
├── calculator.html     # Interactive 24-entry survey UI
├── understanding.html  # Educational knowledge base & kink guide
├── past.html           # Historical result archives
├── about.html          # Project ethos & background information
├── styles.css          # Custom utility styles & neon-glow overlays
└── script.js           # Core StyleExplorer class, questionnaire & scoring engine
```

---

## Disclaimer
KinkXKnow is created for educational, self-exploration, and entertainment purposes only. It does not constitute medical, psychological, or professional relationship counseling.

BDSM and alternative dynamics depend strictly on active consent, clear communication, and safe practices. Always establish firm boundaries, safewords, and mutual understanding with your partner prior to engaging in play.

---

<div align="center">

**Created by Dibyanshu Kumar (Lucifer)**
