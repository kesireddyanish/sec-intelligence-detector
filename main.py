from fastapi import FastAPI
import requests
import json
from bs4 import BeautifulSoup
from database import SessionLocal, InsiderTrade
from apscheduler.schedulers.background import BackgroundScheduler
import contextlib

def fetch_and_save_sec_data():
    print("Fetching SEC data")
    headers = {
        "User-Agent": "Anish Kesireddy anish@example.com"
    }
    cik = "0000320193"
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    #get the company data
    response = requests.get(url, headers=headers)
    company_data = response.json()
    recent_filings = company_data['filings']['recent']
    forms = recent_filings['form']
    accession_no = recent_filings['accessionNumber']
    primary_docs = recent_filings["primaryDocument"]
    #get the recent form 4 filings
    for i in range(len(forms)):
        if forms[i] == "4":
            #remove the dashes from the accession number
            acc_no = accession_no[i].replace("-", "")
            xml_file = primary_docs[i].split("/")[-1]
            cik_no = str(int(cik))
            #get the xml file
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
            
            db = SessionLocal()
            new_trade = InsiderTrade(
                company="Apple",
                share_owner=share_owner,
                is_director=is_director,
                transaction_code=transaction_code,
                shares_traded=float(shares),
                price=float(price),
                total_value=float(total_value)
            )
            
            db.add(new_trade)
            db.commit()
            db.close()
            print("Background Job: Data saved successfully!")
            break
#set up scheduler to run every hour
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    fetch_and_save_sec_data() 
    scheduler.add_job(fetch_and_save_sec_data, 'interval', hours=1) 
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(title="SEC Filings API", lifespan=lifespan)

#get the home page
@app.get("/")
def home():
    return {"message": "Welcome to the SEC Filings API!"}
#get all the trades from the database
@app.get("/api/insider-trades")
def get_insider_trades():
    db = SessionLocal()
    trades = db.query(InsiderTrade).all()
    db.close()
    return trades