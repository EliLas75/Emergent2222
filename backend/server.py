from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import pandas as pd
import io
import re
import numpy as np

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class FinancialData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    raw_data: List[Dict[str, Any]]
    detected_columns: Dict[str, str]
    kpis: Dict[str, float]

class FinancialDataCreate(BaseModel):
    filename: str
    raw_data: List[Dict[str, Any]]

class KPIResponse(BaseModel):
    revenus_totaux: float
    ebitda: float
    resultat_net: float
    free_cash_flow: float
    marge_nette: float

# Financial column detection patterns
COLUMN_PATTERNS = {
    'revenus': ['revenus', 'revenue', 'sales', 'ventes', 'chiffre_affaires', 'ca', 'turnover', 'income'],
    'charges': ['charges', 'expenses', 'costs', 'depenses', 'charges_operationnelles', 'operating_expenses'],
    'ebitda': ['ebitda', 'earnings_before_interest_taxes_depreciation_amortization'],
    'resultat_operationnel': ['resultat_operationnel', 'operating_income', 'operating_result', 'ebit'],
    'amortissements': ['amortissements', 'depreciation', 'amortization', 'depreciation_amortization'],
    'resultat_net': ['resultat_net', 'net_income', 'net_profit', 'benefice_net', 'profit'],
    'impots': ['impots', 'taxes', 'tax', 'impot_societes'],
    'cash_flow': ['cash_flow', 'cashflow', 'flux_tresorerie'],
    'investissements': ['investissements', 'investments', 'capex', 'capital_expenditure'],
    'date': ['date', 'periode', 'month', 'mois', 'year', 'annee', 'trimestre', 'quarter']
}

def detect_columns(df: pd.DataFrame) -> Dict[str, str]:
    """Detect financial columns in the dataframe"""
    detected = {}
    columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
    
    for financial_type, patterns in COLUMN_PATTERNS.items():
        for col_idx, col in enumerate(columns):
            for pattern in patterns:
                if pattern in col or col in pattern:
                    detected[financial_type] = df.columns[col_idx]
                    break
            if financial_type in detected:
                break
    
    return detected

def clean_numeric_value(value) -> float:
    """Clean and convert numeric values"""
    if pd.isna(value) or value == '' or value is None:
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    # Remove currency symbols, spaces, and convert comma decimals
    str_value = str(value).strip()
    str_value = re.sub(r'[€$£¥₹\s]', '', str_value)
    str_value = str_value.replace(',', '.')
    
    try:
        return float(str_value)
    except ValueError:
        return 0.0

def calculate_kpis(df: pd.DataFrame, detected_columns: Dict[str, str]) -> Dict[str, float]:
    """Calculate financial KPIs"""
    kpis = {
        'revenus_totaux': 0.0,
        'ebitda': 0.0,
        'resultat_net': 0.0,
        'free_cash_flow': 0.0,
        'marge_nette': 0.0
    }
    
    # Clean and sum numeric columns
    def get_column_sum(column_type: str) -> float:
        if column_type in detected_columns:
            col_name = detected_columns[column_type]
            if col_name in df.columns:
                return sum(clean_numeric_value(val) for val in df[col_name])
        return 0.0
    
    # 1. Total Revenue
    kpis['revenus_totaux'] = get_column_sum('revenus')
    
    # 2. EBITDA calculation
    resultat_op = get_column_sum('resultat_operationnel')
    amortissements = get_column_sum('amortissements')
    if resultat_op > 0:
        kpis['ebitda'] = resultat_op + amortissements
    else:
        # Fallback: Revenue - Operating Expenses
        revenus = kpis['revenus_totaux']
        charges = get_column_sum('charges')
        kpis['ebitda'] = revenus - charges
    
    # 3. Net Income
    net_income = get_column_sum('resultat_net')
    if net_income > 0:
        kpis['resultat_net'] = net_income
    else:
        # Fallback calculation: EBITDA - Taxes - Interest
        revenus = kpis['revenus_totaux']
        charges = get_column_sum('charges')
        impots = get_column_sum('impots')
        kpis['resultat_net'] = revenus - charges - impots
    
    # 4. Free Cash Flow
    cash_flow = get_column_sum('cash_flow')
    investissements = get_column_sum('investissements')
    if cash_flow > 0:
        kpis['free_cash_flow'] = cash_flow - investissements
    else:
        # Approximate with Net Income
        kpis['free_cash_flow'] = kpis['resultat_net'] - investissements
    
    # 5. Net Margin (%)
    if kpis['revenus_totaux'] > 0:
        kpis['marge_nette'] = (kpis['resultat_net'] / kpis['revenus_totaux']) * 100
    
    return kpis

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Financial Analytics API"}

@api_router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Upload and process CSV file"""
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Read CSV
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Detect columns
        detected_columns = detect_columns(df)
        
        # Calculate KPIs
        kpis = calculate_kpis(df, detected_columns)
        
        # Prepare data for storage
        financial_data = FinancialData(
            filename=file.filename,
            raw_data=df.to_dict('records'),
            detected_columns=detected_columns,
            kpis=kpis
        )
        
        # Store in MongoDB
        await db.financial_data.insert_one(financial_data.dict())
        
        return JSONResponse({
            "id": financial_data.id,
            "filename": file.filename,
            "detected_columns": detected_columns,
            "kpis": kpis,
            "data_preview": df.head(5).to_dict('records')
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@api_router.get("/financial-data/{data_id}")
async def get_financial_data(data_id: str):
    """Get financial data by ID"""
    try:
        data = await db.financial_data.find_one({"id": data_id})
        if not data:
            raise HTTPException(status_code=404, detail="Financial data not found")
        
        return JSONResponse(data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving data: {str(e)}")

@api_router.get("/financial-data")
async def get_all_financial_data():
    """Get all financial data"""
    try:
        data_list = await db.financial_data.find().to_list(100)
        return JSONResponse(data_list)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving data: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()