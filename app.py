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
    
    # Debug logging
    print(f"Formatting item: {item.get('Name', 'Unknown')} with ID: {identifier}")
    
    result = {
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
    
    print(f"Formatted result: {result}")
    return result

@app.route('/api/search/funds', methods=['GET'])
def search_funds():
    """Search for funds globally using Morningstar data"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        country = request.args.get('country', None)  # Optional country parameter
        
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
        
        # Search with optional country restriction
        search_params = {
            'term': term,
            'field': fields,
            'pageSize': page_size * 2
        }
        
        if country:
            search_params['country'] = country
            if country.lower() == 'au':
                search_params['currency'] = 'AUD'
        
        response = mstarpy.search_funds(**search_params)
        
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
            'total_found': len(formatted_results),
            'country': country
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
        country = request.args.get('country', None)  # Optional country parameter
        
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
        
        # Search with optional country restriction
        search_params = {
            'term': term,
            'field': fields,
            'pageSize': page_size * 2
        }
        
        if country:
            if country.lower() == 'au':
                search_params['exchange'] = 'XASX'  # Australian Securities Exchange
            # For other countries, we could add more exchange mappings
        
        response = mstarpy.search_stock(**search_params)
        
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
            'total_found': len(formatted_results),
            'country': country
        })
        
    except Exception as e:
        print(f"Error in search_stocks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/australia', methods=['GET'])
def search_australia():
    """Search specifically in Australian Morningstar data (morningstar.com.au)"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        search_type = request.args.get('type', 'combined')  # 'funds', 'stocks', or 'combined'
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        print(f"Australian search: term='{term}', type='{search_type}', pageSize={page_size}")
        
        all_results = []
        
        # Search Australian funds
        if search_type in ['funds', 'combined']:
            try:
                print(f"Searching Australian funds for: {term}")
                funds_response = mstarpy.search_funds(
                    term=term,
                    field=[
                        "Name", "fundShareClassId", "SecId", "Ticker", "TenforeId",
                        "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                        "ongoingCharge", "globalAssetClassId", "LargestSector", "MarketCountryName", 
                        "currency", "ExchangeId", "CategoryName", "FeeLevel", "starRating"
                    ],
                    country="au",  # Specifically target Australian data
                    currency="AUD",
                    pageSize=page_size if search_type == 'funds' else page_size // 2
                )
                
                print(f"Found {len(funds_response)} Australian funds")
                
                for item in funds_response:
                    try:
                        formatted_item = format_investment_data(item)
                        if formatted_item['apir'] and formatted_item['name']:
                            formatted_item['type'] = 'Fund'
                            formatted_item['source'] = 'Morningstar Australia'
                            all_results.append(formatted_item)
                    except Exception as e:
                        print(f"Error formatting fund item: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error searching Australian funds: {e}")
        
        # Search Australian stocks (ASX)
        if search_type in ['stocks', 'combined']:
            try:
                print(f"Searching ASX stocks for: {term}")
                stocks_response = mstarpy.search_stock(
                    term=term,
                    field=[
                        "Name", "fundShareClassId", "SecId", "Ticker", "TenforeId",
                        "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                        "SectorName", "IndustryName", "ExchangeId", "MarketCountryName", "currency"
                    ],
                    exchange='XASX',  # Australian Securities Exchange
                    pageSize=page_size if search_type == 'stocks' else page_size // 2
                )
                
                print(f"Found {len(stocks_response)} ASX stocks")
                
                for item in stocks_response:
                    try:
                        formatted_item = format_investment_data(item)
                        formatted_item['tcr'] = None  # Stocks don't have ongoing charges
                        if formatted_item['apir'] and formatted_item['name']:
                            formatted_item['type'] = 'Stock'
                            formatted_item['source'] = 'ASX via Morningstar Australia'
                            all_results.append(formatted_item)
                    except Exception as e:
                        print(f"Error formatting stock item: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error searching ASX stocks: {e}")
        
        print(f"Total Australian results: {len(all_results)}")
        
        return jsonify({
            'success': True,
            'results': all_results[:page_size],
            'count': len(all_results[:page_size]),
            'total_found': len(all_results),
            'country': 'Australia',
            'source': 'Morningstar Australia'
        })
        
    except Exception as e:
        print(f"Error in search_australia: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/combined', methods=['GET'])
def search_combined():
    """Search for both funds and stocks with a single term"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        country = request.args.get('country', None)  # Optional country parameter
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        all_results = []
        
        # Search funds first
        try:
            search_params = {
                'term': term,
                'field': [
                    "Name", "fundShareClassId", "SecId", "Ticker", "TenforeId",
                    "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                    "ongoingCharge", "globalAssetClassId", "LargestSector", "MarketCountryName", "currency", "ExchangeId"
                ],
                'pageSize': page_size
            }
            
            if country:
                search_params['country'] = country
                if country.lower() == 'au':
                    search_params['currency'] = 'AUD'
            
            funds_response = mstarpy.search_funds(**search_params)
            
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
                stock_search_params = {
                    'term': term,
                    'field': [
                        "Name", "fundShareClassId", "SecId", "Ticker", "TenforeId",
                        "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                        "SectorName", "IndustryName", "ExchangeId", "MarketCountryName", "currency"
                    ],
                    'pageSize': page_size - len(all_results)
                }
                
                if country and country.lower() == 'au':
                    stock_search_params['exchange'] = 'XASX'
                
                stocks_response = mstarpy.search_stock(**stock_search_params)
                
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
            'total_found': len(all_results),
            'country': country
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
        'endpoints': [
            '/api/health', 
            '/api/search/funds', 
            '/api/search/stocks', 
            '/api/search/combined',
            '/api/search/australia'
        ],
        'country_support': {
            'global': 'Search all markets globally',
            'australia': 'Search Australian data specifically (morningstar.com.au with APIR codes)',
            'other_countries': 'Add ?country=us, ?country=uk etc. to target specific countries'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("Starting Global Morningstar API server...")
    app.run(debug=True, host='0.0.0.0', port=port)
