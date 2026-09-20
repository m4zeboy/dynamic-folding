# Project Overview: dynamic-folding (End-to-End)

## 1. Vision & Purpose
`dynamic-folding` is an **offline, Windows-first semantic organization tool**. It helps users make sense of cluttered directories (like a folder full of hundreds of digital certificates) by proposing a logical folder structure based on file **meaning**, not just filenames.

It is designed as a research platform for a TCC (Thesis) to compare different Machine Learning approaches to file organization.

---

## 2. The Intelligence Pipeline (Step-by-Step)
When you run the tool, every file passes through a seven-stage pipeline:

1.  **Scanner:** Finds all files in the target directory (up to a specific depth).
2.  **Extractor (Type-Aware):** Inspects the files. If it's a PDF, it "reads" metadata and text. For Office docs (.docx, .pptx), it uses "Smart Structural Extraction" to prioritize headings and slide titles. If it's an image, it reads EXIF data.
3.  **Preprocessor:** Combines the metadata into a "Semantic String" using a hybrid template (e.g., `"{stem} {title} {snippet}"`). It prioritizes internal titles over filenames for a stronger semantic signal.
4.  **Embedding (SBERT) + Adaptive Pooling:** Converts text into mathematical vectors. For long documents, it uses **sliding-window chunking** and **Mean Pooling** to ensure the entire document "DNA" is captured, even if it exceeds the model's token limit (e.g., 512 tokens).
5.  **Clustering:** Groups the vectors.
    *   **K-Means:** Force-groups files into `K` clusters.
    *   **Agglomerative Tree:** Builds a family tree of files and "cuts" it at the most logical level.
    *   **HDBSCAN:** Finds "natural" dense groups and identifies outliers (noise).
6.  **Naming (LLM/TF-IDF):** Analyzes the files in a group and proposes a folder name (e.g., "Python Certificates"). It uses local **Ollama** or falls back to keyword extraction.
7.  **Proposer & Renderer:** Builds the final structure and prepares it for the TUI or terminal output.

---

## 3. Key Research Features (TCC Ready)
To support scientific validation, the tool includes:

### The Matrix (Automated Grid Search)
A powerful command (`benchmark`) that automatically tests dozens of combinations of algorithms and settings. It produces a "Leaderboard" to prove which configuration is mathematically superior for a specific dataset.

### The Cohesion Score (Silhouette)
Every proposal is graded from **-1.0 to +1.0**. 
*   **> 0.5:** High confidence, very logical organization.
*   **< 0.2:** Weak signal, likely boilerplate-heavy or messy data.

### Interactive Triage (Unified TUI)
A professional, state-aware application that guides you from folder selection to real-time processing and final review. It includes:
*   **Visual File Browser:** Pick folders without typing paths.
*   **Real-time Progress:** Watch each stage of the ML pipeline (Scanning, Embedding, etc.) as it happens.
*   **Human-in-the-loop:** Review proposals with color-coded confidence levels (Green/Yellow/Red).

---

## 4. Architectural Rules
*   **Offline Only:** No data ever leaves your machine. It uses local Sentence-Transformers and local Ollama.
*   **Plugin-Based:** Every stage (Clustering, Namer, etc.) is a plugin. You can swap "K-Means" for "HDBSCAN" just by changing one line in the config.
*   **Contract-Driven:** Modules don't know about each other; they only know the "Data Contracts" (standardized JSON-like objects) they exchange.

---

## 5. How to Use
1.  **Launch the Unified TUI (Recommended):**
    `uv run dynamic-folding tui`
2.  **Run a research benchmark:**
    `uv run dynamic-folding benchmark "C:/Users/MyFiles"`
3.  **Tune settings:**
    Modify `config/default.toml` to change how deep the tool scans or how it reads files.
