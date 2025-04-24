import os
import logging
from typing import Optional, Any
from pydantic import Field, FilePath

# Import base tool and schemas
from karo.tools.base_tool import BaseTool, BaseToolInputSchema, BaseToolOutputSchema

# Import necessary libraries for file reading
try:
    import pypdf
except ImportError:
    pypdf = None # Handle optional dependency

try:
    import docx
except ImportError:
    docx = None # Handle optional dependency

logger = logging.getLogger(__name__)

# --- Tool Schemas ---

class DocumentReaderInput(BaseToolInputSchema):
    file_path: FilePath = Field(..., description="Path to the document file (txt, md, pdf, docx).")

class DocumentReaderOutput(BaseToolOutputSchema):
    content: Optional[str] = Field(None, description="Extracted text content from the document.")
    file_path: Optional[str] = Field(None, description="Path of the file read.") # Add file_path for clarity

# --- Tool Implementation ---

class DocumentReaderTool(BaseTool):
    input_schema = DocumentReaderInput
    output_schema = DocumentReaderOutput
    name = "document_reader"
    description = "Reads text content from specified document files (txt, md, pdf, docx)."

    # Store required library checks
    pdf_enabled: bool = pypdf is not None
    docx_enabled: bool = docx is not None

    def __init__(self, config: Optional[Any] = None):
        """Initialize the DocumentReaderTool."""
        logger.info(f"DocumentReaderTool initialized. PDF support: {self.pdf_enabled}, DOCX support: {self.docx_enabled}")
        if not self.pdf_enabled:
            logger.warning("pypdf library not found. PDF reading will be disabled. Install with `pip install pypdf` or `poetry add pypdf`.")
        if not self.docx_enabled:
            logger.warning("python-docx library not found. DOCX reading will be disabled. Install with `pip install python-docx` or `poetry add python-docx`.")
        pass # No specific config needed for now

    def run(self, input_data: DocumentReaderInput) -> DocumentReaderOutput:
        """
        Reads the text content from the specified document file.

        Args:
            input_data: An instance of DocumentReaderInput containing the file path.

        Returns:
            An instance of DocumentReaderOutput with the extracted content or an error.
        """
        if not isinstance(input_data, self.input_schema):
            return self.output_schema(success=False, error_message="Invalid input data format.")

        file_path_str = str(input_data.file_path)

        if not os.path.exists(file_path_str):
            return self.output_schema(success=False, error_message=f"File not found: {file_path_str}", file_path=file_path_str)

        _, file_extension = os.path.splitext(file_path_str)
        file_extension = file_extension.lower()

        extracted_content = None
        error_message = None
        success = False

        try:
            if file_extension in ['.txt', '.md']:
                with open(file_path_str, 'r', encoding='utf-8') as f:
                    extracted_content = f.read()
                success = True
                logger.info(f"Successfully read text/markdown file: {file_path_str}")

            elif file_extension == '.pdf':
                if not self.pdf_enabled:
                    error_message = "PDF processing requires the 'pypdf' library. Please install it."
                else:
                    try:
                        reader = pypdf.PdfReader(file_path_str)
                        text_parts = [page.extract_text() for page in reader.pages if page.extract_text()]
                        extracted_content = "\n".join(text_parts)
                        success = True
                        logger.info(f"Successfully read PDF file: {file_path_str}")
                    except Exception as pdf_err:
                        error_message = f"Error reading PDF file: {pdf_err}"
                        logger.error(f"Error reading PDF {file_path_str}: {pdf_err}", exc_info=True)

            elif file_extension == '.docx':
                if not self.docx_enabled:
                    error_message = "DOCX processing requires the 'python-docx' library. Please install it."
                else:
                    try:
                        doc = docx.Document(file_path_str)
                        text_parts = [para.text for para in doc.paragraphs if para.text]
                        extracted_content = "\n".join(text_parts)
                        success = True
                        logger.info(f"Successfully read DOCX file: {file_path_str}")
                    except Exception as docx_err:
                        error_message = f"Error reading DOCX file: {docx_err}"
                        logger.error(f"Error reading DOCX {file_path_str}: {docx_err}", exc_info=True)

            else:
                error_message = f"Unsupported file type: {file_extension}. Supported types: .txt, .md, .pdf, .docx"
                logger.warning(f"Attempted to read unsupported file type: {file_path_str}")

        except Exception as e:
            error_message = f"An unexpected error occurred while reading file: {e}"
            logger.error(f"Unexpected error reading {file_path_str}: {e}", exc_info=True)

        return self.output_schema(
            success=success,
            content=extracted_content,
            error_message=error_message,
            file_path=file_path_str
        )

# Example Usage (for basic manual testing if needed)
# if __name__ == "__main__":
#     tool = DocumentReaderTool()
#     # Create dummy files first
#     # txt_input = DocumentReaderInput(file_path="dummy.txt")
#     # pdf_input = DocumentReaderInput(file_path="dummy.pdf")
#     # docx_input = DocumentReaderInput(file_path="dummy.docx")
#     # output = tool.run(txt_input)
#     # print(output.model_dump_json(indent=2))