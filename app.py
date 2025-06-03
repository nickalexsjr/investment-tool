from flask import Flask, request, jsonify
from flask_cors import CORS
import mstarpy
import pandas as pd
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

def format_investment_data(item):
    """Format investment data to match your frontend structure"""
    # Try to get Australian APIR code
    apir_code = item.get('fundShareClassId', '') or item.get('SecId', '') or item.get('Ticker', '')
    
    return {
        'apir': apir_code,
        'name': item.get('Name', ''),
        'threeMonths': item.get('GBRReturnM3', None),
        'oneYear': item.get('GBRReturnM12', None),
        'threeYears': item.get('GBRReturnM36', None),
        'fiveYears': item.get('GBRReturnM60', None),
        'tenYears': item.get('GBRReturnM120', None),
        'tcr': item.get('ongoingCharge', None),
        'assetClass': item.get('globalAssetClassId', 'Australian'),
        'sector': item.get('LargestSector', ''),
        'status': 'Morningstar Data'
    }

def filter_australian_results(results):
    """Filter to only Australian investments"""
    australian_results = []
    for item in results:
        apir = item.get('apir', '')
        name = item.get('name', '').lower()
        
        # Filter for Australian investments
        if (apir.endswith('AU') or 
            'australia' in name or 
            'asx' in name.lower() or
            'aud' in name.lower()):
            australian_results.append(item)
    
    return australian_results

@app.route('/api/search/funds', methods=['GET'])
def search_funds():
    """Search for Australian funds using Morningstar data"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        # Search specifically in Australian market
        fields = [
            "Name", 
            "fundShareClassId",
            "SecId",
            "Ticker", 
            "GBRReturnM3",   # 3 months
            "GBRReturnM12",  # 1 year  
            "GBRReturnM36",  # 3 years
            "GBRReturnM60",  # 5 years
            "GBRReturnM120", # 10 years
            "ongoingCharge", # TCR equivalent
            "globalAssetClassId",
            "LargestSector",
            "MarketCountryName"
        ]
        
        # Force Australian search
        response = mstarpy.search_funds(
            term=term,
            field=fields,
            country="au",  # Force Australia
            pageSize=page_size * 3,  # Get more results to filter
            currency="AUD"
        )
        
        # Format the response
        formatted_results = [format_investment_data(item) for item in response]
        
        # Filter for Australian results only
        australian_results = filter_australian_results(formatted_results)
        
        # Limit to requested page size
        final_results = australian_results[:page_size]
        
        return jsonify({
            'success': True,
            'results': final_results,
            'count': len(final_results),
            'total_found': len(australian_results)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/stocks', methods=['GET'])
def search_stocks():
    """Search for Australian stocks using Morningstar data"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        # Search specifically on ASX
        fields = [
            "Name", 
            "fundShareClassId",
            "SecId",
            "Ticker",
            "GBRReturnM3",   # 3 months
            "GBRReturnM12",  # 1 year
            "GBRReturnM36",  # 3 years  
            "GBRReturnM60",  # 5 years
            "GBRReturnM120", # 10 years
            "SectorName",
            "ExchangeId",
            "MarketCountryName"
        ]
        
        # Force ASX exchange
        response = mstarpy.search_stock(
            term=term,
            field=fields,
            exchange='XASX',  # Australian Securities Exchange
            pageSize=page_size * 2
        )
        
        # Format the response (stocks don't have TCR)
        formatted_results = []
        for item in response:
            # Only include if it's clearly Australian
            market_country = item.get('MarketCountryName', '').lower()
            exchange_id = item.get('ExchangeId', '').lower()
            
            if 'australia' in market_country or 'xasx' in exchange_id:
                formatted_item = format_investment_data(item)
                formatted_item['tcr'] = None  # Stocks don't have ongoing charges
                formatted_item['sector'] = item.get('SectorName', '')
                formatted_results.append(formatted_item)
        
        # Limit results
        final_results = formatted_results[:page_size]
        
        return jsonify({
            'success': True, 
            'results': final_results,
            'count': len(final_results)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Australian Morningstar API is running'})

@app.route('/')
def home():
    """Basic home route"""
    return jsonify({
        'message': 'Australian Investment Performance API with Morningstar is running',
        'status': 'live',
        'market': 'Australia (APIR codes ending in AU)',
        'endpoints': ['/api/health', '/api/search/funds', '/api/search/stocks']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("Starting Australian Morningstar API server...")
    app.run(debug=True, host='0.0.0.0', port=port)
