from PyPDF2 import PdfReader
import re
import pandas as pd

# Load the PDF again for processing
pdf_path = 'C:/Users/alexj/OneDrive/Documents/GitHub/DataMining/BuroBS/AmCham-Guatemala-Membership-Directory-2021.pdf'
reader = PdfReader(pdf_path)
all_text = ""

# Extract text from all pages
for page in reader.pages:
    all_text += page.extract_text()

# Function to extract structured data around emails
def extract_structured_data(text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.finditer(email_pattern, text)
    data = []

    for match in matches:
        email = match.group()
        # Extract context for other fields
        start_idx = max(match.start() - 150, 0)
        end_idx = match.end() + 150
        context = text[start_idx:end_idx]

        # Extract fields using basic patterns
        name_match = re.search(r'\b[A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?\b', context)
        company_match = re.search(r'(?<=\n)[A-Z][A-Za-z &,-]+(?=\n)', context)
        title_match = re.search(r'(Manager|Director|CEO|President|Vice President|Coordinator|Gerente|Encargado)', context, re.IGNORECASE)

        name = name_match.group() if name_match else None
        company = company_match.group() if company_match else None
        title = title_match.group() if title_match else None

        data.append({
            "Email": email,
            "Nombre": name,
            "Cargo": title,
            "Compañía": company
        })

    return data

# Process the text to extract structured data
structured_data = extract_structured_data(all_text)

# Convert to DataFrame
df_structured = pd.DataFrame(structured_data)

# Display a preview of the structured data
df_structured.head()


# Create a DataFrame from the emails
email_df = pd.DataFrame(df_structured)

# Save to a CSV file
output_path = "Extracted_Emails_AmCham_GT.csv"
email_df.to_csv(output_path, index=False)

output_path