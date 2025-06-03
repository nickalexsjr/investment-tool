from flask import Flask, request, jsonify
from flask_cors import CORS
import mstarpy
import pandas as pd
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

def is_genuine_australian_investment(item, formatted_item):
    """Check if this is genuinely an Australian investment with proper codes"""
    
    # Check for proper APIR code format
    apir_code = formatted_item.get('apir', '')
    if apir_code:
        # Australian APIR codes typically end with 'AU' and are 8-9 characters
        if apir_code.upper().endswith('AU') and len(apir_code) >= 8:
            print(f"✓ Valid APIR code found: {apir_code}")
            return True
        
        # Some may have different formats but still be Australian
        if any(x in apir_code.upper() for x in ['TGP', 'ANZ', 'CBA', 'WBC', 'NAB']) and 'AU' in apir_code.upper():
            print(f"✓ Recognized Australian fund code: {apir_code}")
            return True
    
    # Check for proper Australian exchange
    exchange = formatted_item.get('exchange', '').upper()
    if exchange in ['XASX', 'ASX', 'AORD']:
        print(f"✓ Australian exchange found: {exchange}")
        return True
    
    # Check for explicit Australian country marking
    country = formatted_item.get('country', '').lower()
    if 'australia' in country:
        print(f"✓ Australian country found: {country}")
        return True
    
    # Check for AUD currency
    currency = formatted_item.get('currency', '').upper()
    fund_name = formatted_item.get('name', '').lower()
    
    # If it has AUD currency AND mentions Australia in the name
    if currency == 'AUD' and any(x in fund_name for x in ['australia', 'aussie', 'asx']):
        print(f"✓ AUD currency with Australian name: {fund_name}")
        return True
    
    # Reject obvious non-Australian codes
    if apir_code and (
        apir_code.startswith('F0000') or  # Morningstar internal codes
        'XXX' in apir_code or 
        len(apir_code) > 12 or  # Too long for APIR
        any(x in exchange for x in ['$

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
    """Search specifically in Australian Morningstar data with multiple strategies"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        search_type = request.args.get('type', 'combined')
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        print(f"=== AUSTRALIAN SEARCH: {term} ===")
        
        all_results = []
        
        # Search Australian funds with multiple strategies
        if search_type in ['funds', 'combined']:
            print(f"Searching Australian funds...")
            
            # Strategy 1: Direct Australian search
            fund_results = []
            
            # Try multiple search approaches
            search_strategies = [
                # Strategy 1: Direct AU country search
                {
                    'country': 'au',
                    'currency': 'AUD',
                    'name': 'Direct AU search'
                },
                # Strategy 2: AUD currency only
                {
                    'currency': 'AUD',
                    'name': 'AUD currency search'
                },
                # Strategy 3: No restrictions (global search, filter later)
                {
                    'name': 'Global search (filter later)'
                }
            ]
            
            enhanced_fields = [
                "Name", "FundName", "SecurityName", "LegalName",
                "fundShareClassId", "SecId", "Ticker", "TenforeId", 
                "APIR", "apir", "ApirCode", "APIR_Code", "FundId", "InvestmentId", "Code", "Symbol",
                "isin", "ISIN", "PermID",
                "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                "ReturnM3", "ReturnM12", "ReturnM36", "ReturnM60", "ReturnM120",
                "ongoingCharge", "ManagementFee", "ExpenseRatio", "TotalExpenseRatio", "AnnualReportExpenseRatio",
                "globalAssetClassId", "AssetClass", "LargestSector", "SectorName", "Sector",
                "MarketCountryName", "Country", "DomicileCountry", "LegalDomicile",
                "currency", "Currency", "BaseCurrency", "ExchangeId", "Exchange", 
                "CategoryName", "FeeLevel", "starRating", "MorningstarRating",
                "FundSize", "TotalAssets", "NetAssets", "AUM"
            ]
            
            for strategy in search_strategies:
                try:
                    print(f"Trying strategy: {strategy['name']}")
                    
                    search_params = {
                        'term': term,
                        'field': enhanced_fields,
                        'pageSize': 100  # Get more results for filtering
                    }
                    
                    # Add strategy-specific parameters
                    if 'country' in strategy:
                        search_params['country'] = strategy['country']
                    if 'currency' in strategy:
                        search_params['currency'] = strategy['currency']
                    
                    strategy_results = mstarpy.search_funds(**search_params)
                    print(f"Strategy '{strategy['name']}' returned {len(strategy_results)} results")
                    
                    # Process and validate results
                    for item in strategy_results:
                        try:
                            formatted_item = format_investment_data(item)
                            if formatted_item['name'] and is_australian_investment(item, formatted_item):
                                formatted_item['type'] = 'Fund'
                                formatted_item['source'] = 'Morningstar Australia'
                                formatted_item['search_strategy'] = strategy['name']
                                fund_results.append(formatted_item)
                        except Exception as e:
                            continue
                    
                    # If we got good results from this strategy, we can break
                    if len(fund_results) >= 10:
                        print(f"Got sufficient results from strategy: {strategy['name']}")
                        break
                        
                except Exception as e:
                    print(f"Error with strategy '{strategy['name']}': {e}")
                    continue
            
            all_results.extend(fund_results)
            print(f"Total fund results after all strategies: {len(fund_results)}")
        
        # Search Australian stocks (ASX)
        if search_type in ['stocks', 'combined']:
            print(f"Searching ASX stocks...")
            
            stock_results = []
            
            # ASX search strategies
            stock_strategies = [
                # Strategy 1: Direct ASX exchange search
                {
                    'exchange': 'XASX',
                    'name': 'XASX exchange search'
                },
                # Strategy 2: Alternative ASX search
                {
                    'exchange': 'ASX',
                    'name': 'ASX exchange search'
                },
                # Strategy 3: AUD currency stocks
                {
                    'currency': 'AUD',
                    'name': 'AUD stocks search'
                }
            ]
            
            stock_fields = [
                "Name", "SecurityName", "CompanyName",
                "fundShareClassId", "SecId", "Ticker", "TenforeId", "Symbol", "Code",
                "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                "ReturnM3", "ReturnM12", "ReturnM36", "ReturnM60", "ReturnM120",
                "SectorName", "IndustryName", "Sector", "Industry",
                "ExchangeId", "Exchange", "MarketCountryName", "Country", 
                "currency", "Currency", "ClosePrice", "LastPrice",
                "MarketCap", "MarketCapitalization", "PERatio", "PE"
            ]
            
            for strategy in stock_strategies:
                try:
                    print(f"Trying stock strategy: {strategy['name']}")
                    
                    search_params = {
                        'term': term,
                        'field': stock_fields,
                        'pageSize': 100
                    }
                    
                    # Add strategy-specific parameters
                    if 'exchange' in strategy:
                        search_params['exchange'] = strategy['exchange']
                    if 'currency' in strategy:
                        search_params['currency'] = strategy['currency']
                    
                    strategy_results = mstarpy.search_stock(**search_params)
                    print(f"Stock strategy '{strategy['name']}' returned {len(strategy_results)} results")
                    
                    for item in strategy_results:
                        try:
                            formatted_item = format_investment_data(item)
                            formatted_item['tcr'] = None  # Stocks don't have ongoing charges
                            if formatted_item['name'] and is_australian_investment(item, formatted_item):
                                formatted_item['type'] = 'Stock'
                                formatted_item['source'] = 'ASX via Morningstar Australia'
                                formatted_item['search_strategy'] = strategy['name']
                                stock_results.append(formatted_item)
                        except Exception as e:
                            continue
                    
                    if len(stock_results) >= 5:
                        print(f"Got sufficient stock results from strategy: {strategy['name']}")
                        break
                        
                except Exception as e:
                    print(f"Error with stock strategy '{strategy['name']}': {e}")
                    continue
            
            all_results.extend(stock_results)
            print(f"Total stock results: {len(stock_results)}")
        
        # Remove duplicates while preserving order
        unique_results = []
        seen = set()
        
        for result in all_results:
            # Create a unique key based on name and code
            key = (result['name'].lower().strip(), result.get('apir', '').upper().strip())
            if key not in seen and key[0]:  # Ensure name is not empty
                seen.add(key)
                unique_results.append(result)
        
        print(f"=== FINAL RESULTS ===")
        print(f"Total unique Australian results: {len(unique_results)}")
        
        return jsonify({
            'success': True,
            'results': unique_results[:page_size],
            'count': len(unique_results[:page_size]),
            'total_found': len(unique_results),
            'country': 'Australia',
            'source': 'Morningstar Australia - Multiple Strategies',
            'debug': {
                'raw_results_count': len(all_results),
                'unique_results_count': len(unique_results),
                'search_term': term,
                'search_type': search_type
            }
        })
        
    except Exception as e:
        print(f"Error in search_australia: {e}")
        import traceback
        traceback.print_exc()
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

@app.route('/api/test/search', methods=['GET'])
def test_search():
    """Test search endpoint to debug specific searches"""
    try:
        term = request.args.get('term', 'TGP0034')
        
        print(f"=== TEST SEARCH FOR: {term} ===")
        
        # Try multiple search strategies like the main function
        strategies_tested = []
        
        try:
            # Test Strategy 1: Direct AU search
            print("Testing Strategy 1: Direct AU search")
            response1 = mstarpy.search_funds(
                term=term,
                country="au",
                currency="AUD",
                pageSize=50
            )
            
            processed1 = []
            for item in response1:
                formatted = format_investment_data(item)
                is_valid = is_australian_investment(item, formatted)
                processed1.append({
                    'formatted': formatted,
                    'is_valid_australian': is_valid
                })
            
            strategies_tested.append({
                'name': 'Direct AU search',
                'raw_count': len(response1),
                'valid_count': sum(1 for r in processed1 if r['is_valid_australian']),
                'sample_results': processed1[:3]
            })
            
            # Test Strategy 2: AUD currency only
            print("Testing Strategy 2: AUD currency search")
            response2 = mstarpy.search_funds(
                term=term,
                currency="AUD",
                pageSize=50
            )
            
            processed2 = []
            for item in response2:
                formatted = format_investment_data(item)
                is_valid = is_australian_investment(item, formatted)
                processed2.append({
                    'formatted': formatted,
                    'is_valid_australian': is_valid
                })
            
            strategies_tested.append({
                'name': 'AUD currency search',
                'raw_count': len(response2),
                'valid_count': sum(1 for r in processed2 if r['is_valid_australian']),
                'sample_results': processed2[:3]
            })
            
            # Test Strategy 3: Global search
            print("Testing Strategy 3: Global search")
            response3 = mstarpy.search_funds(
                term=term,
                pageSize=50
            )
            
            processed3 = []
            for item in response3:
                formatted = format_investment_data(item)
                is_valid = is_australian_investment(item, formatted)
                processed3.append({
                    'formatted': formatted,
                    'is_valid_australian': is_valid
                })
            
            strategies_tested.append({
                'name': 'Global search',
                'raw_count': len(response3),
                'valid_count': sum(1 for r in processed3 if r['is_valid_australian']),
                'sample_results': processed3[:3]
            })
            
            return jsonify({
                'success': True,
                'term': term,
                'strategies_tested': strategies_tested,
                'summary': {
                    'total_strategies': len(strategies_tested),
                    'best_strategy': max(strategies_tested, key=lambda x: x['valid_count'])['name'],
                    'total_valid_found': sum(s['valid_count'] for s in strategies_tested)
                }
            })
            
        except Exception as e:
            print(f"Error in test search: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            
    except Exception as e:
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
            '/api/search/australia',
            '/api/test/search'
        ],
        'country_support': {
            'global': 'Search all markets globally',
            'australia': 'Multi-strategy search for Australian investments (all APIR formats, AUD currency, ASX stocks)',
            'other_countries': 'Add ?country=us, ?country=uk etc. to target specific countries',
            'test': 'Use /api/test/search?term=XXXX to debug search strategies'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("Starting Global Morningstar API server...")
    app.run(debug=True, host='0.0.0.0', port=port), 'XXX', 'EX$$']) or  # Invalid exchanges
        not apir_code.replace('0', '').replace('F', '')  # Only F's and 0's
    ):
        print(f"✗ Rejected non-Australian code: {apir_code}, exchange: {exchange}")
        return False
    
    print(f"? Uncertain about: {apir_code}, exchange: {exchange}, country: {country}")
    return False

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
                
                # Enhanced field list to capture all possible Australian data
                enhanced_fields = [
                    "Name", "FundName", "SecurityName",
                    "fundShareClassId", "SecId", "Ticker", "TenforeId", 
                    "APIR", "apir", "ApirCode", "APIR_Code", "FundId", "InvestmentId", "Code", "Symbol",
                    "isin", "ISIN",
                    "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                    "ReturnM3", "ReturnM12", "ReturnM36", "ReturnM60", "ReturnM120",  # Alternative return fields
                    "ongoingCharge", "ManagementFee", "ExpenseRatio", "TotalExpenseRatio",
                    "globalAssetClassId", "AssetClass", "LargestSector", "SectorName", "Sector",
                    "MarketCountryName", "Country", "DomicileCountry", 
                    "currency", "Currency", "ExchangeId", "Exchange", 
                    "CategoryName", "FeeLevel", "starRating", "MorningstarRating",
                    "FundSize", "TotalAssets", "NetAssets"
                ]
                
                funds_response = mstarpy.search_funds(
                    term=term,
                    field=enhanced_fields,
                    country="au",  # Specifically target Australian data
                    currency="AUD",
                    pageSize=page_size * 3 if search_type == 'funds' else page_size
                )
                
                print(f"Found {len(funds_response)} Australian funds")
                
                for item in funds_response:
                    try:
                        print(f"Processing fund item: {item}")
                        formatted_item = format_investment_data(item)
                        if formatted_item['name'] and (formatted_item['apir'] or len(formatted_item['name']) > 3):
                            formatted_item['type'] = 'Fund'
                            formatted_item['source'] = 'Morningstar Australia'
                            all_results.append(formatted_item)
                    except Exception as e:
                        print(f"Error formatting fund item: {e}")
                        print(f"Item that caused error: {item}")
                        continue
                        
            except Exception as e:
                print(f"Error searching Australian funds: {e}")
                import traceback
                traceback.print_exc()
        
        # Search Australian stocks (ASX)
        if search_type in ['stocks', 'combined']:
            try:
                print(f"Searching ASX stocks for: {term}")
                
                enhanced_stock_fields = [
                    "Name", "SecurityName", "CompanyName",
                    "fundShareClassId", "SecId", "Ticker", "TenforeId", "Symbol", "Code",
                    "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                    "ReturnM3", "ReturnM12", "ReturnM36", "ReturnM60", "ReturnM120",
                    "SectorName", "IndustryName", "Sector", "Industry",
                    "ExchangeId", "Exchange", "MarketCountryName", "Country", 
                    "currency", "Currency", "ClosePrice", "LastPrice",
                    "MarketCap", "MarketCapitalization", "PERatio", "PE"
                ]
                
                stocks_response = mstarpy.search_stock(
                    term=term,
                    field=enhanced_stock_fields,
                    exchange='XASX',  # Australian Securities Exchange
                    pageSize=page_size * 3 if search_type == 'stocks' else page_size
                )
                
                print(f"Found {len(stocks_response)} ASX stocks")
                
                for item in stocks_response:
                    try:
                        print(f"Processing stock item: {item}")
                        formatted_item = format_investment_data(item)
                        formatted_item['tcr'] = None  # Stocks don't have ongoing charges
                        if formatted_item['name'] and (formatted_item['apir'] or len(formatted_item['name']) > 3):
                            formatted_item['type'] = 'Stock'
                            formatted_item['source'] = 'ASX via Morningstar Australia'
                            all_results.append(formatted_item)
                    except Exception as e:
                        print(f"Error formatting stock item: {e}")
                        print(f"Item that caused error: {item}")
                        continue
                        
            except Exception as e:
                print(f"Error searching ASX stocks: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"Total Australian results found: {len(all_results)}")
        
        # Remove duplicates and sort by relevance
        unique_results = []
        seen_names = set()
        
        for result in all_results:
            result_key = (result['name'].lower(), result['apir'])
            if result_key not in seen_names:
                seen_names.add(result_key)
                unique_results.append(result)
        
        print(f"Unique Australian results: {len(unique_results)}")
        
        return jsonify({
            'success': True,
            'results': unique_results[:page_size],
            'count': len(unique_results[:page_size]),
            'total_found': len(unique_results),
            'country': 'Australia',
            'source': 'Morningstar Australia',
            'debug': {
                'raw_results_count': len(all_results),
                'unique_results_count': len(unique_results),
                'search_term': term,
                'search_type': search_type
            }
        })
        
    except Exception as e:
        print(f"Error in search_australia: {e}")
        import traceback
        traceback.print_exc()
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

@app.route('/api/test/search', methods=['GET'])
def test_search():
    """Test search endpoint to debug specific searches"""
    try:
        term = request.args.get('term', 'TGP0034')
        
        print(f"=== TEST SEARCH FOR: {term} ===")
        
        # Try searching Australian funds with extensive debugging
        try:
            response = mstarpy.search_funds(
                term=term,
                country="au",
                currency="AUD",
                pageSize=50
            )
            
            print(f"Raw response type: {type(response)}")
            print(f"Raw response length: {len(response) if hasattr(response, '__len__') else 'N/A'}")
            print(f"Raw response sample: {response[:2] if hasattr(response, '__len__') and len(response) > 0 else response}")
            
            return jsonify({
                'success': True,
                'term': term,
                'raw_response': response,
                'count': len(response) if hasattr(response, '__len__') else 0
            })
            
        except Exception as e:
            print(f"Error in test search: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            
    except Exception as e:
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
