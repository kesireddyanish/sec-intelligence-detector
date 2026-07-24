from fastapi import FastAPI
import requests
import json
from bs4 import BeautifulSoup

app = FastAPI(title="SEC Filings API")

@app.get("/")
def home():
    return {"message": "Welcome to the SEC Filings API!"}


@app.get("/api/apple")
def get_apple_insider_data():
    headers = {
        "User-Agent": "Anish Kesireddy anish@example.com"
    }
    cik = "0000320193"
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    
    response = requests.get(url, headers=headers)
    company_data = response.json()
    recent_filings = company_data['filings']['recent']
    forms = recent_filings['form']
    accession_no = recent_filings['accessionNumber']
    primary_docs = recent_filings["primaryDocument"]
    
    for i in range(len(forms)):
        if forms[i] == "4":
            acc_no = accession_no[i].replace("-", "")
            xml_file = primary_docs[i].split("/")[-1]
            cik_no = str(int(cik))

            xml_url = f"https://www.sec.gov/Archives/edgar/data/{cik_no}/{acc_no}/{xml_file}"
            xml_response = requests.get(xml_url, headers=headers)
            soup = BeautifulSoup(xml_response.content, 'xml')

            share_owner = soup.find("rptOwnerName").text if soup.find("rptOwnerName") else "Unknown"
            is_director = soup.find("isDirector").text if soup.find("isDirector") else "Unknown"
            
            code_tag = soup.find("transactionCode")
            transaction_code = code_tag.text.strip() if code_tag else "Unknown"

            shares_tag = soup.find("transactionShares")
            price_tag = soup.find("transactionPricePerShare")
            
            shares = shares_tag.text.strip() if shares_tag and shares_tag.text.strip() else "0"
            price = price_tag.text.strip() if price_tag and price_tag.text.strip() else "0.0"
            total_value = int(float(shares)) * float(price)
            
            #return JSON format for api
            return {
                "company": "Apple",
                "share_owner": share_owner,
                "is_director": is_director,
                "transaction_code": transaction_code,
                "shares_traded": shares,
                "price": price,
                "total_value": round(total_value, 2)
            }