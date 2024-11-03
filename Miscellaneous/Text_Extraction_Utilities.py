import pdfplumber
import tiktoken

def extract_pdf_text_plumber(pdf_path):
    pdf_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pdf_text += page.extract_text()
    return pdf_text

# # Example usage
# pdf_path = "/content/drive/MyDrive/Colab Notebooks/pymdp/biofirm_data/A. CPA - DIA_Clippinger 2024.pdf"
# try:
#     extracted_text = extract_pdf_text_plumber(pdf_path)
#     print("PDF content extracted successfully!")
# except Exception as e:
#     print(f"An error occurred: {str(e)}")

def count_tokens(text="",model="gpt-4o-mini"):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

#count_tokens(extracted_text)