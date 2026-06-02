import sys

def run_pypdf_demo():
    print("\n--- RUNNING PYPDF DEMO ---")
    from pypdf import PdfReader

    # Example 1: Simple text document
    try:
        reader1 = PdfReader("NIRM03_SelfLearning_ASR_Kazakh_Updated.pdf")
        page1 = reader1.pages[2]
        text1 = page1.extract_text()
        print("=" * 50)
        print("PYPDF: SIMPLE TEXT - page 3")
        print("=" * 50)
        print(text1[:1500])
        print("...")
    except Exception as e:
        print(f"Error reading simple text with pypdf: {e}")

    # Example 2: Complex table document
    try:
        reader2 = PdfReader("09_2025_Consolidated Financial statements_IFRS_RUS.pdf")
        page2 = reader2.pages[22]
        text2 = page2.extract_text()
        print("\n" + "=" * 50)
        print("PYPDF: COMPLEX TABLE - page 23")
        print("=" * 50)
        print(text2)
        print("\n" + "=" * 50)
        print("CONCLUSION: Table structure is lost with pypdf!")
        print("Columns merge and data becomes misaligned because it extracts text line-by-line.")
        print("=" * 50)
    except Exception as e:
        print(f"Error reading complex table with pypdf: {e}")

def run_docling_demo():
    print("\n--- RUNNING DOCLING DEMO ---")
    from docling.document_converter import DocumentConverter

    # Docling Example 1: Simple text document
    try:
        converter = DocumentConverter()
        print("Docling converting simple document...")
        result = converter.convert("NIRM03_SelfLearning_ASR_Kazakh_Updated.pdf")
        markdown_text = result.document.export_to_markdown()
        print("=" * 50)
        print("DOCLING: SIMPLE TEXT - markdown export (first 1500 chars)")
        print("=" * 50)
        print(markdown_text[:1500])
        print("...")
    except Exception as e:
        print(f"Error converting simple document with docling: {e}")

    # Docling Example 2: Complex table document
    try:
        converter = DocumentConverter()
        print("Docling converting complex table document...")
        result2 = converter.convert("09_2025_Consolidated Financial statements_IFRS_RUS (1)-pages.pdf")
        markdown_text2 = result2.document.export_to_markdown()
        print("\n" + "=" * 50)
        print("DOCLING: COMPLEX TABLE - markdown export")
        print("=" * 50)
        print(markdown_text2)
        print("\n" + "=" * 50)
        print("CONCLUSION: Docling preserves the table structure!")
        print("Tables are converted into standard Markdown tables, maintaining rows and columns.")
        print("=" * 50)
    except Exception as e:
        print(f"Error converting complex table with docling: {e}")

if __name__ == "__main__":
    run_pypdf_demo()
    run_docling_demo()
