import os
from openai import OpenAI
from supabase import create_client, Client
from typing import List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up application...")
    logger.info("Checking environment variables...")
    if not all([os.getenv('OPENAI_API_KEY'), os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')]):
        logger.error("Missing required environment variables!")
    else:
        logger.info("All required environment variables are set")

class BrandRequest(BaseModel):
    brand_name: str

def find_competitors(brand_name: str) -> List[str]:
    """
    Use OpenAI to find 5 competitor brands with loyalty programs
    """
    prompt = f"""Find 5 major competitors of {brand_name} that have loyalty programs. 
    Return only the brand names separated by commas, nothing else."""
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that provides competitor analysis."},
            {"role": "user", "content": prompt}
        ]
    )
    
    competitors = response.choices[0].message.content.strip().split(',')
    return [comp.strip() for comp in competitors]

def insert_competitors(brand_name: str, competitors: List[str]):
    """
    Insert competitors into Supabase table with both brand_name and competitor_name
    """
    for competitor in competitors:
        supabase.table('competitors').insert({
            'brand_name': brand_name,
            'competitor_name': competitor
        }).execute()

@app.post("/analyze-competitors")
async def analyze_competitors(request: BrandRequest):
    try:
        if not all([os.getenv('OPENAI_API_KEY'), os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')]):
            raise HTTPException(status_code=500, detail="Missing environment variables")
        
        competitors = find_competitors(request.brand_name)
        insert_competitors(request.brand_name, competitors)
        
        return {
            "brand_name": request.brand_name,
            "competitors": competitors,
            "status": "Data successfully stored in Supabase"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"status": "API is running"}
