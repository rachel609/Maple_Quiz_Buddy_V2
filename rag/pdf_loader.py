"""
PDF Loader - Load and chunk the Discover Canada PDF.

Purpose: Read PDF, split into chunks for RAG retrieval.
Inputs: PDF file path.
Outputs: List of Document objects with page content and metadata.
Dependencies: config, pypdf, langchain-text-splitters.
"""
import os
import config

MOCK_CHUNKS = [
    {"content": "Canada is a constitutional monarchy and a federal state with a democratic parliament. "
     "The Sovereign is Queen Elizabeth II, who is also the Sovereign of 15 other Commonwealth countries.",
     "metadata": {"source": "discover_canada.pdf", "page": 1, "chapter": "Modern Canada"}},
    {"content": "Canadians enjoy many rights and freedoms, including mobility rights, Aboriginal peoples' rights, "
     "official language rights, and minority language educational rights.",
     "metadata": {"source": "discover_canada.pdf", "page": 5, "chapter": "Rights and Responsibilities"}},
    {"content": "The Parliament of Canada has three parts: the Sovereign (Queen), the Senate, and the House of Commons. "
     "Provincial legislatures are called legislative assemblies.",
     "metadata": {"source": "discover_canada.pdf", "page": 12, "chapter": "How Canadians Govern Themselves"}},
    {"content": "Sir John A. Macdonald was the first Prime Minister of Canada. He was instrumental in the creation "
     "of the Canadian Pacific Railway, which united Canada from east to west.",
     "metadata": {"source": "discover_canada.pdf", "page": 20, "chapter": "Canadian History"}},
    {"content": "Canada has ten provinces and three territories. Each province has its own elected legislature. "
     "The three territories are Northwest Territories, Yukon, and Nunavut.",
     "metadata": {"source": "discover_canada.pdf", "page": 30, "chapter": "Regions of Canada"}},
    {"content": "The Canadian Charter of Rights and Freedoms was entrenched in the Constitution in 1982. "
     "It begins with fundamental freedoms including freedom of conscience, religion, thought, expression, "
     "peaceful assembly, and association.",
     "metadata": {"source": "discover_canada.pdf", "page": 6, "chapter": "Rights and Responsibilities"}},
    {"content": "Canada's economy is one of the largest in the world. Key industries include natural resources, "
     "manufacturing, and services. Canada is a trading nation with major exports to the United States.",
     "metadata": {"source": "discover_canada.pdf", "page": 35, "chapter": "Canada's Economy"}},
    {"content": "To become a Canadian citizen, you must be a permanent resident, have lived in Canada for at least "
     "3 out of the last 5 years, have filed your taxes, and pass a citizenship test.",
     "metadata": {"source": "discover_canada.pdf", "page": 2, "chapter": "Applying for Citizenship"}},
    {"content": "The maple leaf is Canada's most recognized symbol. The national anthem is 'O Canada'. "
     "Canada Day is celebrated on July 1st, marking the anniversary of Confederation in 1867.",
     "metadata": {"source": "discover_canada.pdf", "page": 40, "chapter": "Canadian Symbols"}},
    {"content": "The three levels of government in Canada are federal, provincial/territorial, and municipal. "
     "The federal government is responsible for national defence, foreign affairs, and immigration.",
     "metadata": {"source": "discover_canada.pdf", "page": 14, "chapter": "How Canadians Govern Themselves"}},
]


def load_pdf_chunks(pdf_path: str = None) -> list:
    """
    Load and chunk a PDF file. In sandbox mode, returns mock chunks.
    Returns a list of dicts with 'content' and 'metadata' keys.
    """
    if config.is_sandbox():
        return MOCK_CHUNKS

    pdf_path = pdf_path or config.PDF_PATH
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        from pypdf import PdfReader
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        reader = PdfReader(pdf_path)
        full_text = ""
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            full_text += f"\n[Page {i+1}]\n{text}"

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " "],
        )
        chunks = splitter.split_text(full_text)

        return [
            {"content": chunk, "metadata": {"source": os.path.basename(pdf_path), "chunk_index": i}}
            for i, chunk in enumerate(chunks)
        ]
    except Exception as e:
        raise RuntimeError(f"Failed to load PDF: {e}")


if __name__ == "__main__":
    chunks = load_pdf_chunks()
    print(f"Loaded {len(chunks)} chunks")
    for c in chunks[:3]:
        print(f"  [{c['metadata']}] {c['content'][:80]}...")
