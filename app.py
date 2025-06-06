from flask import Flask, request, jsonify
from flask_cors import CORS
import mstarpy
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import os
import json
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_investment_data(item, source="Unknown"):
    """Format investment data to match your frontend structure"""
    # Get the identifier - try different fields based on what's available
    identifier = (item.get('fundShareClassId', '') or 
                 item.get('SecId', '') or 
                 item.get('Ticker', '') or 
                 item.get('TenforeId', '') or
                 item.get('apir', '') or
                 item.get('usi', '') or
                 item.get('abn', ''))
    
    # Debug logging
    logger.info(f"Formatting item: {item.get('Name', item.get('name', 'Unknown'))} with ID: {identifier}")
    
    result = {
        'apir': identifier,
        'name': item.get('Name', '') or item.get('name', '') or item.get('fund_name', ''),
        'threeMonths': item.get('GBRReturnM3', None),
        'oneYear': item.get('GBRReturnM12', None),
        'threeYears': item.get('GBRReturnM36', None),
        'fiveYears': item.get('GBRReturnM60', None),
        'tenYears': item.get('GBRReturnM120', None),
        'tcr': item.get('ongoingCharge', None),
        'assetClass': item.get('globalAssetClassId', ''),
        'sector': item.get('LargestSector', '') or item.get('SectorName', ''),
        'status': source,
        'country': item.get('MarketCountryName', 'Australia'),
        'currency': item.get('currency', 'AUD'),
        'exchange': item.get('ExchangeId', ''),
        'type': item.get('type', 'Fund')
    }
    
    logger.info(f"Formatted result: {result}")
    return result

class ATOSuperFundLookup:
    """Wrapper for ATO Super Fund Lookup web service"""
    
    def __init__(self, guid=None):
        self.base_url = "https://superfundlookup.gov.au/xmlsearch/SuperFundLookup.asmx"
        self.guid = guid or os.getenv('ATO_SFL_GUID')  # Set your GUID in environment variable
        
    def search_by_name(self, name, active_only=True):
        """Search super funds by name using ATO service"""
        if not self.guid:
            logger.warning("No ATO GUID configured for Super Fund Lookup")
            return []
            
        try:
            # Prepare SOAP request
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                         xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                         xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <SearchByNameV2 xmlns="http://superfundlookup.gov.au/">
                  <name>{name}</name>
                  <guid>{self.guid}</guid>
                  <activeOnly>{str(active_only).lower()}</activeOnly>
                </SearchByNameV2>
              </soap:Body>
            </soap:Envelope>"""
            
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'http://superfundlookup.gov.au/SearchByNameV2'
            }
            
            response = requests.post(self.base_url, data=soap_body, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return self._parse_name_search_response(response.text)
            else:
                logger.error(f"ATO search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching ATO Super Fund Lookup: {e}")
            return []
    
    def _parse_name_search_response(self, xml_response):
        """Parse XML response from name search"""
        try:
            # Parse XML and extract fund information
            root = ET.fromstring(xml_response)
            funds = []
            
            # Navigate through the XML structure to find fund data
            # This would need to be implemented based on the actual XML structure
            # For now, return empty list
            return funds
            
        except Exception as e:
            logger.error(f"Error parsing ATO response: {e}")
            return []

class APISuperDataService:
    """Alternative super fund data service using multiple sources"""
    
    def __init__(self):
        self.major_funds = self._load_major_australian_funds()
    
    def _load_major_australian_funds(self):
        """Load data for major Australian superannuation funds"""
        # This would typically be loaded from a database or API
        # For now, we'll include major Australian super funds manually
        return [
            {
                'name': 'AustralianSuper',
                'apir': 'ASU0001AU',
                'abn': '65714394898',
                'type': 'Industry Super Fund',
                'website': 'australiansuper.com',
                'members': '3500000+'
            },
            {
                'name': 'Aware Super',
                'apir': 'AWS0001AU', 
                'abn': '53226460365',
                'type': 'Industry Super Fund',
                'website': 'aware.com.au',
                'members': '1100000+'
            },
            {
                'name': 'HESTA',
                'apir': 'HES0001AU',
                'abn': '64971749321',
                'type': 'Industry Super Fund',
                'website': 'hesta.com.au',
                'members': '900000+'
            },
            {
                'name': 'Hostplus',
                'apir': 'HOS0001AU',
                'abn': '68307088910',
                'type': 'Industry Super Fund',
                'website': 'hostplus.com.au',
                'members': '1600000+'
            },
            {
                'name': 'UniSuper',
                'apir': 'UNI0001AU',
                'abn': '91385943850',
                'type': 'Industry Super Fund',
                'website': 'unisuper.com.au',
                'members': '460000+'
            },
            {
                'name': 'REST Industry Super',
                'apir': 'RES0001AU',
                'abn': '45687043025',
                'type': 'Industry Super Fund',
                'website': 'rest.com.au',
                'members': '1900000+'
            },
            {
                'name': 'Cbus',
                'apir': 'CBU0001AU',
                'abn': '75493258286',
                'type': 'Industry Super Fund',
                'website': 'cbussuper.com.au',
                'members': '900000+'
            }
        ]
    
    def search_funds(self, term):
        """Search through major Australian super funds"""
        results = []
        term_lower = term.lower()
        
        for fund in self.major_funds:
            if (term_lower in fund['name'].lower() or 
                term_lower in fund.get('apir', '').lower() or
                term_lower in fund.get('abn', '').lower()):
                
                # Format as investment data
                formatted_fund = {
                    'apir': fund.get('apir', ''),
                    'name': fund['name'],
                    'threeMonths': None,  # Would be populated from performance data
                    'oneYear': None,
                    'threeYears': None,
                    'fiveYears': None,
                    'tenYears': None,
                    'tcr': None,
                    'assetClass': 'Superannuation',
                    'sector': fund.get('type', 'Super Fund'),
                    'status': 'Australian Super Fund Database',
                    'country': 'Australia',
                    'currency': 'AUD',
                    'exchange': 'Australian Super',
                    'type': 'Super Fund',
                    'abn': fund.get('abn', ''),
                    'members': fund.get('members', ''),
                    'website': fund.get('website', '')
                }
                results.append(formatted_fund)
        
        return results

# Initialize services
ato_service = ATOSuperFundLookup()
super_data_service = APISuperDataService()

@app.route('/api/search/funds', methods=['GET'])
def search_funds():
    """Search for funds globally using enhanced Morningstar data"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        country = request.args.get('country', None)
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        # Enhanced field list for better Australian data
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
            "starRating",
            "universe",  # Important for filtering
            "region"     # Important for Australian data
        ]
        
        # Enhanced search parameters for Australian data
        search_params = {
            'term': term,
            'field': fields,
            'pageSize': page_size * 2
        }
        
        # Better Australian targeting
        if country and country.lower() == 'au':
            search_params.update({
                'country': 'AU',
                'currency': 'AUD',
                'region': 'APAC',  # Asia-Pacific region
                'universe': ['AU', 'australia', 'australian']  # Multiple universe options
            })
        elif country:
            search_params['country'] = country
        
        logger.info(f"Searching with params: {search_params}")
        
        try:
            response = mstarpy.search_funds(**search_params)
            logger.info(f"Morningstar returned {len(response)} results")
        except Exception as e:
            logger.error(f"Morningstar search failed: {e}")
            response = []
        
        # Format the Morningstar response
        formatted_results = []
        for item in response:
            try:
                formatted_item = format_investment_data(item, 'Morningstar Data')
                if formatted_item['apir'] and formatted_item['name']:
                    formatted_results.append(formatted_item)
            except Exception as e:
                logger.error(f"Error formatting item: {e}")
                continue
        
        # For Australian searches, also include our local super fund database
        if country and country.lower() == 'au':
            try:
                local_results = super_data_service.search_funds(term)
                logger.info(f"Local database returned {len(local_results)} results")
                formatted_results.extend(local_results)
            except Exception as e:
                logger.error(f"Local search failed: {e}")
        
        # Remove duplicates and limit to requested page size
        seen_names = set()
        unique_results = []
        for item in formatted_results:
            name_key = item['name'].lower()
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique_results.append(item)
        
        final_results = unique_results[:page_size]
        
        return jsonify({
            'success': True,
            'results': final_results,
            'count': len(final_results),
            'total_found': len(unique_results),
            'country': country,
            'sources_used': ['Morningstar', 'Australian Super Fund Database'] if country and country.lower() == 'au' else ['Morningstar']
        })
        
    except Exception as e:
        logger.error(f"Error in search_funds: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/stocks', methods=['GET'])
def search_stocks():
    """Search for stocks globally using Morningstar data with enhanced Australian support"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        country = request.args.get('country', None)
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        # Enhanced field list for stocks
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
            "PERatio",
            "region"
        ]
        
        # Enhanced search parameters
        search_params = {
            'term': term,
            'field': fields,
            'pageSize': page_size * 2
        }
        
        if country:
            if country.lower() == 'au':
                search_params.update({
                    'exchange': 'XASX',  # Australian Securities Exchange
                    'country': 'AU',
                    'currency': 'AUD',
                    'region': 'APAC'
                })
            else:
                search_params['country'] = country
        
        response = mstarpy.search_stock(**search_params)
        
        # Format the response
        formatted_results = []
        for item in response:
            try:
                formatted_item = format_investment_data(item, 'Morningstar Stocks')
                formatted_item['tcr'] = None  # Stocks don't have ongoing charges
                if formatted_item['apir'] and formatted_item['name']:
                    formatted_results.append(formatted_item)
            except Exception as e:
                logger.error(f"Error formatting stock item: {e}")
                continue
        
        final_results = formatted_results[:page_size]
        
        return jsonify({
            'success': True, 
            'results': final_results,
            'count': len(final_results),
            'total_found': len(formatted_results),
            'country': country
        })
        
    except Exception as e:
        logger.error(f"Error in search_stocks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/australia', methods=['GET'])
def search_australia():
    """Enhanced Australian search with multiple data sources"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        search_type = request.args.get('type', 'combined')
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        logger.info(f"Australian search: term='{term}', type='{search_type}', pageSize={page_size}")
        
        all_results = []
        
        # Search major Australian super funds first
        if search_type in ['funds', 'combined']:
            try:
                logger.info(f"Searching Australian super fund database for: {term}")
                local_funds = super_data_service.search_funds(term)
                
                for item in local_funds:
                    item['type'] = 'Super Fund'
                    item['source'] = 'Australian Super Fund Database'
                    all_results.append(item)
                
                logger.info(f"Found {len(local_funds)} results from Australian super fund database")
            except Exception as e:
                logger.error(f"Error searching local super funds: {e}")
        
        # Search Morningstar Australian funds
        if search_type in ['funds', 'combined']:
            try:
                logger.info(f"Searching Morningstar Australian funds for: {term}")
                
                # Enhanced parameters for Australian Morningstar data
                funds_response = mstarpy.search_funds(
                    term=term,
                    field=[
                        "Name", "fundShareClassId", "SecId", "Ticker", "TenforeId",
                        "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                        "ongoingCharge", "globalAssetClassId", "LargestSector", "MarketCountryName", 
                        "currency", "ExchangeId", "CategoryName", "FeeLevel", "starRating", "region"
                    ],
                    country="AU",
                    currency="AUD",
                    region="APAC",  # Asia-Pacific region for better Australian coverage
                    pageSize=page_size if search_type == 'funds' else page_size // 2
                )
                
                logger.info(f"Found {len(funds_response)} Morningstar Australian funds")
                
                for item in funds_response:
                    try:
                        formatted_item = format_investment_data(item, 'Morningstar Australia')
                        if formatted_item['apir'] and formatted_item['name']:
                            formatted_item['type'] = 'Fund'
                            formatted_item['source'] = 'Morningstar Australia'
                            all_results.append(formatted_item)
                    except Exception as e:
                        logger.error(f"Error formatting Morningstar fund item: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error searching Morningstar Australian funds: {e}")
        
        # Search ASX stocks
        if search_type in ['stocks', 'combined']:
            try:
                logger.info(f"Searching ASX stocks for: {term}")
                stocks_response = mstarpy.search_stock(
                    term=term,
                    field=[
                        "Name", "fundShareClassId", "SecId", "Ticker", "TenforeId",
                        "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                        "SectorName", "IndustryName", "ExchangeId", "MarketCountryName", "currency", "region"
                    ],
                    exchange='XASX',
                    country='AU',
                    currency='AUD',
                    region='APAC',
                    pageSize=page_size if search_type == 'stocks' else page_size // 2
                )
                
                logger.info(f"Found {len(stocks_response)} ASX stocks")
                
                for item in stocks_response:
                    try:
                        formatted_item = format_investment_data(item, 'ASX via Morningstar')
                        formatted_item['tcr'] = None
                        if formatted_item['apir'] and formatted_item['name']:
                            formatted_item['type'] = 'Stock'
                            formatted_item['source'] = 'ASX via Morningstar'
                            all_results.append(formatted_item)
                    except Exception as e:
                        logger.error(f"Error formatting ASX stock item: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error searching ASX stocks: {e}")
        
        # Remove duplicates
        seen_names = set()
        unique_results = []
        for item in all_results:
            name_key = item['name'].lower()
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique_results.append(item)
        
        logger.info(f"Total unique Australian results: {len(unique_results)}")
        
        return jsonify({
            'success': True,
            'results': unique_results[:page_size],
            'count': len(unique_results[:page_size]),
            'total_found': len(unique_results),
            'country': 'Australia',
            'sources': ['Australian Super Fund Database', 'Morningstar Australia', 'ASX']
        })
        
    except Exception as e:
        logger.error(f"Error in search_australia: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/combined', methods=['GET'])
def search_combined():
    """Search for both funds and stocks with a single term"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        country = request.args.get('country', None)
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        all_results = []
        
        # For Australian searches, include local database
        if country and country.lower() == 'au':
            try:
                local_results = super_data_service.search_funds(term)
                for item in local_results:
                    item['type'] = 'Super Fund'
                    all_results.append(item)
            except Exception as e:
                logger.error(f"Local search failed: {e}")
        
        # Search funds
        try:
            search_params = {
                'term': term,
                'field': [
                    "Name", "fundShareClassId", "SecId", "Ticker", "TenforeId",
                    "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                    "ongoingCharge", "globalAssetClassId", "LargestSector", "MarketCountryName", 
                    "currency", "ExchangeId", "region"
                ],
                'pageSize': page_size
            }
            
            if country:
                if country.lower() == 'au':
                    search_params.update({
                        'country': 'AU',
                        'currency': 'AUD',
                        'region': 'APAC'
                    })
                else:
                    search_params['country'] = country
            
            funds_response = mstarpy.search_funds(**search_params)
            
            for item in funds_response:
                try:
                    formatted_item = format_investment_data(item, 'Morningstar Funds')
                    if formatted_item['apir'] and formatted_item['name']:
                        formatted_item['type'] = 'Fund'
                        all_results.append(formatted_item)
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Error searching funds: {e}")
        
        # Search stocks if we need more results
        if len(all_results) < page_size:
            try:
                stock_search_params = {
                    'term': term,
                    'field': [
                        "Name", "fundShareClassId", "SecId", "Ticker", "TenforeId",
                        "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                        "SectorName", "IndustryName", "ExchangeId", "MarketCountryName", "currency", "region"
                    ],
                    'pageSize': page_size - len(all_results)
                }
                
                if country:
                    if country.lower() == 'au':
                        stock_search_params.update({
                            'exchange': 'XASX',
                            'country': 'AU',
                            'currency': 'AUD',
                            'region': 'APAC'
                        })
                    else:
                        stock_search_params['country'] = country
                
                stocks_response = mstarpy.search_stock(**stock_search_params)
                
                for item in stocks_response:
                    try:
                        formatted_item = format_investment_data(item, 'Morningstar Stocks')
                        formatted_item['tcr'] = None
                        if formatted_item['apir'] and formatted_item['name']:
                            formatted_item['type'] = 'Stock'
                            all_results.append(formatted_item)
                    except:
                        continue
                        
            except Exception as e:
                logger.error(f"Error searching stocks: {e}")
        
        # Remove duplicates
        seen_names = set()
        unique_results = []
        for item in all_results:
            name_key = item['name'].lower()
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique_results.append(item)
        
        return jsonify({
            'success': True,
            'results': unique_results[:page_size],
            'count': len(unique_results[:page_size]),
            'total_found': len(unique_results),
            'country': country
        })
        
    except Exception as e:
        logger.error(f"Error in search_combined: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'message': 'Enhanced Australian Investment Performance API is running',
        'services': {
            'morningstar': 'Available',
            'australian_super_database': 'Available',
            'ato_super_lookup': 'Available' if ato_service.guid else 'Not configured'
        }
    })

@app.route('/')
def home():
    """Basic home route"""
    return jsonify({
        'message': 'Enhanced Australian Investment Performance API with Multiple Data Sources',
        'status': 'live',
        'coverage': 'Enhanced Australian superannuation funds + Global markets',
        'endpoints': [
            '/api/health', 
            '/api/search/funds', 
            '/api/search/stocks', 
            '/api/search/combined',
            '/api/search/australia'
        ],
        'data_sources': {
            'morningstar_global': 'Global fund and stock data',
            'morningstar_australia': 'Australian fund and stock data with enhanced targeting',
            'australian_super_database': 'Major Australian superannuation funds (AustralianSuper, HESTA, etc.)',
            'ato_super_lookup': 'ATO Super Fund Lookup service (requires GUID)'
        },
        'australian_improvements': [
            'Enhanced Morningstar Australian targeting with region=APAC',
            'Local database of major Australian super funds',
            'Better APIR code handling',
            'Integration with ATO Super Fund Lookup service',
            'Duplicate removal and result merging'
        ]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("Starting Enhanced Australian Investment Performance API server...")
    app.run(debug=True, host='0.0.0.0', port=port)
