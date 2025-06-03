from flask import Flask, request, jsonify
from flask_cors import CORS
import mstarpy
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

def format_investment_data(item):
    """Format investment data to match your frontend structure"""
    return {
        'apir': item.get('fundShareClassId', ''),
        'name': item.get('Name', ''),
        'threeMonths': item.get('GBRReturnM3', None),
        'oneYear': item.get('GBRReturnM12', None),
        'threeYears': item.get('GBRReturnM36', None),
        'fiveYears': item.get('GBRReturnM60', None),
        'tenYears': item.get('GBRReturnM120', None),
        'tcr': item.get('ongoingCharge', None),
        'assetClass': item.get('globalAssetClassId', 'Unknown'),
        'sector': item.get('LargestSector', ''),
        'status': 'Morningstar Data'
    }

@app.route('/api/search/funds', methods=['GET'])
def search_funds():
    """Search for funds using Morningstar data"""
    try:
        term = request.args.get('term', '')
        country = request.args.get('country', 'au')  # Default to Australia
        page_size = int(request.args.get('pageSize', 20))
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        # Search for funds using mstarpy
        fields = [
            "Name", 
            "fundShareClassId", 
            "GBRReturnM3",   # 3 months
            "GBRReturnM12",  # 1 year  
            "GBRReturnM36",  # 3 years
            "GBRReturnM60",  # 5 years
            "GBRReturnM120", # 10 years
            "ongoingCharge", # TCR equivalent
            "globalAssetClassId",
            "LargestSector"
        ]
        
        response = mstarpy.search_funds(
            term=term,
            field=fields,
            country=country,
            pageSize=page_size,
            currency="AUD"
        )
        
        # Format the response to match your frontend structure
        formatted_results = [format_investment_data(item) for item in response]
        
        return jsonify({
            'success': True,
            'results': formatted_results,
            'count': len(formatted_results)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/stocks', methods=['GET'])
def search_stocks():
    """Search for stocks using Morningstar data"""
    try:
        term = request.args.get('term', '')
        exchange = request.args.get('exchange', 'XASX')  # Default to ASX
        page_size = int(request.args.get('pageSize', 20))
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        # Search for stocks using mstarpy
        fields = [
            "Name", 
            "fundShareClassId", 
            "GBRReturnM3",   # 3 months
            "GBRReturnM12",  # 1 year
            "GBRReturnM36",  # 3 years  
            "GBRReturnM60",  # 5 years
            "GBRReturnM120", # 10 years
            "SectorName"
        ]
        
        response = mstarpy.search_stock(
            term=term,
            field=fields,
            exchange=exchange,
            pageSize=page_size
        )
        
        # Format the response (stocks don't have TCR, so set to None)
        formatted_results = []
        for item in response:
            formatted_item = format_investment_data(item)
            formatted_item['tcr'] = None  # Stocks don't have ongoing charges
            formatted_item['sector'] = item.get('SectorName', '')
            formatted_results.append(formatted_item)
        
        return jsonify({
            'success': True, 
            'results': formatted_results,
            'count': len(formatted_results)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Morningstar API is running'})

if __name__ == '__main__':
    print("Starting Morningstar API server...")
    app.run(debug=True, port=5000)
