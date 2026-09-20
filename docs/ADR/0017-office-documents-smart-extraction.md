# ADR 0017: Office Documents Smart Extraction

## Status
Accepted

## Context
The `dynamic-folding` pipeline relies heavily on the quality of the semantic signal extracted from files. Currently, the `type_aware` extractor supports plain text and PDFs (up to a 4KB snippet limit) and Images (EXIF metadata). However, in real-world corporate or academic environments, Microsoft Office documents (`.docx`, `.pptx`) are prevalent. 

Reading the entirety of these documents is computationally expensive (I/O) and dilutes the semantic signal if standard mean-pooling is applied to large amounts of boilerplate text. Alternatively, simply reading the first 4KB of raw text might capture only the title page, table of contents, or legal disclaimers, missing the core topic of the document.

## Decision
We will implement "Smart Structural Extraction" for `.docx` and `.pptx` files within the `type_aware` extractor.

1.  **Optional Dependencies:** We will use `python-docx` and `python-pptx`. To adhere to the project's philosophy of avoiding forced bloat, these will be *optional* dependencies (e.g., installable via `uv pip install -e .[office]`). If they are missing at runtime, the pipeline will gracefully fall back to basic file metadata extraction without crashing.
2.  **Structural Prioritization:** 
    *   For `.docx`, the extractor will prioritize paragraphs styled as "Heading" or "Title".
    *   For `.pptx`, the extractor will prioritize text from Title placeholders and Header shapes on the first few slides.
3.  **Hard Size Limit:** The total extracted text will still be strictly capped at the configured `snippet_size` (default 4096 bytes) to maintain performance and avoid overwhelming the embedding chunker. If the high-value structural text does not reach the limit, the extractor will backfill with standard body paragraphs.

## Consequences

### Positive
*   **Higher Quality Grouping:** By targeting headings and titles, the text sent to the SBERT model will be dense with semantic meaning, ignoring boilerplate, leading to more accurate clustering and naming.
*   **Robustness:** The graceful degradation ensures that users without the specific Python libraries can still run the tool without failures.
*   **Performance Maintained:** The `snippet_size` limit ensures that scanning a massive presentation won't stall the pipeline.

### Negative
*   **Complexity:** The extractor logic becomes slightly more complex, needing to parse internal XML structures rather than raw bytes.
*   **Testing Overhead:** We must rely heavily on mocked tests since we cannot guarantee the presence of the libraries or actual Office files in the CI environment without bloating the repository.
