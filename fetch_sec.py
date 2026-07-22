import requests
import json
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Anish Kesireddy anish@example.com"
}
cik = "0000320193"
url = f"https://data.sec.gov/submissions/CIK{cik}.json"
response = requests.get(url, headers=headers)
company_data = response.json()
print(company_data.keys())
#get the recent ones using the filings and recent keys
recent_filings = company_data['filings']['recent']

forms = recent_filings['form']
accession_no = recent_filings['accessionNumber']
primary_docs = recent_filings["primaryDocument"]
dates = recent_filings["filingDate"]

print("Total recent filings found: " + str(len(forms)))

count = 0
for i in range(len(forms)):
    if(forms[i] == "4"):
        print("Found Form 4 filing on " + str(dates[i]))
        print("Accession Number: " + accession_no[i])
        print("Primary Document: " + primary_docs[i])
        count += 1
        print()

    if(count >= 5):
        break
for i in range(len(forms)):
    if(forms[i] == "4"):
        #get the last part of the primary doc to get the xml file
        accession_no[i] = accession_no[i].replace("-", "")
        xml_file = primary_docs[i].split("/")[-1]
        cik_no = str(int(cik))

        xml_url = "https://www.sec.gov/Archives/edgar/data/" + cik_no + "/" + accession_no[i] + "/" + xml_file
        xml_response = requests.get(xml_url, headers = headers)
        soup = BeautifulSoup(xml_response.content, 'xml')

        #find if the person who had a transaction with the company is a director or not

        if(soup.find("rptOwnerName")):
            share_owner = soup.find("rptOwnerName").text
        else:
            share_owner = "Unknown"

        if(soup.find("isDirector")):
            is_director = soup.find("isDirector").text
        else:
            is_director = "Unknown"
        
         #find the price and shares they did the transaction on
        shares_tag = soup.find("transactionShares")
        price_tag = soup.find("transactionPricePerShare")
        
        #take out blnk spaces and if it's missing, default to "0"
        shares = shares_tag.text.strip() if shares_tag and shares_tag.text.strip() else "0"
        price = price_tag.text.strip() if price_tag and price_tag.text.strip() else "0.0"
        
        #print everything
        print("Share owner: " + share_owner)
        print("Is director: " + is_director)
        print("Number of shares bought: " + shares)
        print("Price per share: " + price)
        
        #find the total value of the transaction
        total_value = int(float(shares)) * float(price)
        print("Total value of transaction: $" + str(round(total_value, 2)))
        print("-" * 30)
        
        #stop after the first 5 transaction
        break
