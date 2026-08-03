from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json
from bs4 import BeautifulSoup
from database import SessionLocal, InsiderTrade, WatchlistCompany
from apscheduler.schedulers.background import BackgroundScheduler
import contextlib
import time

def fetch_and_save_sec_data():
    print("Fetching SEC data...")
    headers = {
        "User-Agent": "Anish Kesireddy anish@example.com"
    }
    
    #open database connection
    db = SessionLocal()
    #fetch all companies from database
    watchlist = db.query(WatchlistCompany).all()
    
    for company in watchlist:
        try:
            print(f"Fetching data for {company.name}...")
            #CIK is already padded to 10 digits when we save it
            url = f"https://data.sec.gov/submissions/CIK{company.cik}.json"
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Failed to fetch {company.name}: HTTP {response.status_code}")
                time.sleep(0.2)
                continue
                
            company_data = response.json()
            recent_filings = company_data['filings']['recent']
            forms = recent_filings['form']
            accession_no = recent_filings['accessionNumber']
            primary_docs = recent_filings["primaryDocument"]
            
            for i in range(len(forms)):
                if forms[i] == "4":
                    acc_no = accession_no[i].replace("-", "")
                    xml_file = primary_docs[i].split("/")[-1]
                    cik_no = str(int(company.cik)) 

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
                    
                    new_trade = InsiderTrade(
                        company=company.name, 
                        share_owner=share_owner,
                        is_director=is_director,
                        transaction_code=transaction_code,
                        shares_traded=float(shares),
                        price=float(price),
                        total_value=float(total_value)
                    )         
                    db.add(new_trade)
                    db.commit()
                    print(f"Saved latest trade for {company.name}")
                    break 
            time.sleep(0.2)
        except Exception as e:
            print(f"Error fetching {company.name}: {e}")
    db.close()
    print("Watchlist updated")

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

#add function to get the watchlist
class WatchlistRequest(BaseModel):
    company_name: str

@app.post("/api/watchlist")
def add_to_watchlist(request: WatchlistRequest):
    db = SessionLocal()
    
    #enforce the 10 company limit
    count = db.query(WatchlistCompany).count()
    if count >= 10:
        db.close()
        raise HTTPException(status_code=400, detail="Maximum 10 companies allowed in watchlist.")
    #check if already tracking
    existing = db.query(WatchlistCompany).filter(WatchlistCompany.name.ilike(f"%{request.company_name}%")).first()
    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Company already in watchlist.")
    #lookup CIK from SEC
    headers = {"User-Agent": "Anish Kesireddy anish@example.com"}
    response = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers)
    
    if response.status_code != 200:
        db.close()
        raise HTTPException(status_code=500, detail="Failed to reach SEC tickers database.")
    data = response.json()
    #search for the company name
    matched_cik = None
    matched_name = None
    for key, val in data.items():
        if request.company_name.lower() in val['title'].lower() or request.company_name.lower() == val['ticker'].lower():
            #remove the leading zeros from the cik
            matched_cik = str(val['cik_str']).zfill(10)
            matched_name = val['title']
            break
    if not matched_cik:
        db.close()
        raise HTTPException(status_code=404, detail=f"Couldn't find valid SEC CIK for '{request.company_name}'.")
    #add it to the database
    new_company = WatchlistCompany(name=matched_name, cik=matched_cik)
    db.add(new_company)
    db.commit()
    db.close()
    return {"message": f"Added {matched_name} (CIK: {matched_cik}) to watchlist!"}

@app.get("/api/watchlist")
def get_watchlist():
    db = SessionLocal()
    watchlist = db.query(WatchlistCompany).all()
    db.close()
    return watchlist

#api endpoint to get insider trades for a specific company
@app.get("/api/insider-trades/{company_name}")
def get_insider_trades(company_name: str):
    db = SessionLocal()
    trades = db.query(InsiderTrade).filter(InsiderTrade.company == company_name).all()
    db.close()
    return trades