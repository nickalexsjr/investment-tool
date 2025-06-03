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
    # Get the identifier - try different fields based on what's available
    identifier = (item.get('fundShareClassId', '') or 
                 item.get('SecId', '') or 
                 item.get('Ticker', '') or 
                 item.get('TenforeId', ''))
    
    return {
        'apir': identifier,
        'name': item.get('Name', ''),
        'threeMonths': item.get('GBRReturnM3', None),
        'oneYear': item.get('GBRReturnM12', None),
        'threeYears': item.get('GBRReturnM36', None),
        'fiveYears': item.get('GBRReturnM60', None),
        'tenYears': item.get('GBRReturnM120', None),
        'tcr': item.get('ongoingCharge', None),
        'assetClass': item.get('globalAssetClassId', ''),
        'sector': item.get('LargestSector', '') or item.get('SectorName', ''),
        'status': 'Morningstar Data',
        'country': item.get('MarketCountryName', ''),
        'currency': item.get('currency', ''),
        'exchange': item.get('ExchangeId', '')
    }

@app.route('/api/search/funds', methods=['GET'])
def search_funds():
    """Search for funds globally using Morningstar data"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        # Comprehensive field list to get all available data
        fields = [
            "Name", 
            "fundShareClassId",
            "SecId",
            "Ticker", 
            "TenforeId",
            "GBRReturnM3",   # 3 months
            "GBRReturnM12",  # 1 year  
            "GBRReturnM36",  # 3 years
            "GBRReturnM60",  # 5 years
            "GBRReturnM120", # 10 years
            "ongoingCharge", # TCR/Management fees
            "globalAssetClassId",
            "LargestSector",
            "MarketCountryName",
            "currency",
            "ExchangeId",
            "CategoryName",
            "FeeLevel",
            "starRating"
        ]
        
        # Global search - no country restriction
        response = mstarpy.search_funds(
            term=term,
            field=fields,
            pageSize=page_size * 2  # Get more results as some might be filtered
        )
        
        # Format the response
        formatted_results = []
        for item in response:
            try:
                formatted_item = format_investment_data(item)
                # Only include if we have a valid identifier and name
                if formatted_item['apir'] and formatted_item['name']:
                    formatted_results.append(formatted_item)
            except Exception as e:
                print(f"Error formatting item: {e}")
                continue
        
        # Limit to requested page size
        final_results = formatted_results[:page_size]
        
        return jsonify({
            'success': True,
            'results': final_results,
            'count': len(final_results),
            'total_found': len(formatted_results)
        })
        
    except Exception as e:
        print(f"Error in search_funds: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/stocks', methods=['GET'])
def search_stocks():
    """Search for stocks globally using Morningstar data"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        # Comprehensive field list for stocks
        fields = [
            "Name", 
            "fundShareClassId",
            "SecId",
            "Ticker",
            "TenforeId",
            "GBRReturnM3",   # 3 months
            "GBRReturnM12",  # 1 year
            "GBRReturnM36",  # 3 years  
            "GBRReturnM60",  # 5 years
            "GBRReturnM120", # 10 years
            "SectorName",
            "IndustryName",
            "ExchangeId",
            "MarketCountryName",
            "currency",
            "ClosePrice",
            "MarketCap",
            "PERatio"
        ]
        
        # Global search - no exchange restriction
        response = mstarpy.search_stock(
            term=term,
            field=fields,
            pageSize=page_size * 2
        )
        
        # Format the response
        formatted_results = []
        for item in response:
            try:
                formatted_item = format_investment_data(item)
                formatted_item['tcr'] = None  # Stocks don't have ongoing charges
                # Only include if we have a valid identifier and name
                if formatted_item['apir'] and formatted_item['name']:
                    formatted_results.append(formatted_item)
            except Exception as e:
                print(f"Error formatting stock item: {e}")
                continue
        
        # Limit results
        final_results = formatted_results[:page_size]
        
        return jsonify({
            'success': True, 
            'results': final_results,
            'count': len(final_results),
            'total_found': len(formatted_results)
        })
        
    except Exception as e:
        print(f"Error in search_stocks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/combined', methods=['GET'])
def search_combined():
    """Search for both funds and stocks with a single term"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        all_results = []
        
        # Search funds first
        try:
            funds_response = mstarpy.search_funds(
                term=term,
                field=[
                    "Name", "fundShareClassId", "SecId", "Ticker", "TenforeId",
                    "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                    "ongoingCharge", "globalAssetClassId", "LargestSector", "MarketCountryName", "currency", "ExchangeId"
                ],
                pageSize=page_size
            )
            
            for item in funds_response:
                try:
                    formatted_item = format_investment_data(item)
                    if formatted_item['apir'] and formatted_item['name']:
                        formatted_item['type'] = 'Fund'
                        all_results.append(formatted_item)
                except:
                    continue
                    
        except Exception as e:
            print(f"Error searching funds: {e}")
        
        # Search stocks if we need more results
        if len(all_results) < page_size:
            try:
                stocks_response = mstarpy.search_stock(
                    term=term,
                    field=[
                        "Name", "fundShareClassId", "SecId", "Ticker", "TenforeId",
                        "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                        "SectorName", "IndustryName", "ExchangeId", "MarketCountryName", "currency"
                    ],
                    pageSize=page_size - len(all_results)
                )
                
                for item in stocks_response:
                    try:
                        formatted_item = format_investment_data(item)
                        formatted_item['tcr'] = None  # Stocks don't have ongoing charges
                        if formatted_item['apir'] and formatted_item['name']:
                            formatted_item['type'] = 'Stock'
                            all_results.append(formatted_item)
                    except:
                        continue
                        
            except Exception as e:
                print(f"Error searching stocks: {e}")
        
        return jsonify({
            'success': True,
            'results': all_results[:page_size],
            'count': len(all_results[:page_size]),
            'total_found': len(all_results)
        })
        
    except Exception as e:
        print(f"Error in search_combined: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Global Morningstar API is running'})

@app.route('/')
def home():
    """Basic home route"""
    return jsonify({
        'message': 'Global Investment Performance API with Morningstar is running',
        'status': 'live',
        'coverage': 'Global markets (all regions and exchanges)',
        'endpoints': ['/api/health', '/api/search/funds', '/api/search/stocks', '/api/search/combined']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("Starting Global Morningstar API server...")
    app.run(debug=True, host='0.0.0.0', port=port)
