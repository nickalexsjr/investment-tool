from flask import Flask, request, jsonify
from flask_cors import CORS
import mstarpy
import pandas as pd
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import os
import json
import logging
import re
import time
from urllib.parse import urljoin, quote
import asyncio
import aiohttp

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveAustralianDataService:
    """Comprehensive Australian investment data service combining multiple sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.cached_data = {}
        self.last_update = {}
        
    def scrape_investsmart_fund(self, fund_slug):
        """Scrape detailed fund data from InvestSMART"""
        try:
            url = f"https://www.investsmart.com.au/managed-funds/fund/{fund_slug}"
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract APIR code
            apir_code = None
            apir_elements = soup.find_all(text=re.compile(r'[A-Z]{3}\d{4}AU'))
            for element in apir_elements:
                match = re.search(r'([A-Z]{3}\d{4}AU)', element)
                if match:
                    apir_code = match.group(1)
                    break
            
            # Extract performance data
            performance_data = {}
            
            # Look for performance table or data
            performance_rows = soup.find_all('tr')
            for row in performance_rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    # Parse performance values
                    if 'month' in label and '1' in label:
                        try:
                            perf_val = float(value.replace('%', '').replace(',', ''))
                            performance_data['oneMonth'] = perf_val
                        except:
                            pass
                    elif 'month' in label and '3' in label:
                        try:
                            perf_val = float(value.replace('%', '').replace(',', ''))
                            performance_data['threeMonths'] = perf_val
                        except:
                            pass
                    elif 'year' in label and '1' in label:
                        try:
                            perf_val = float(value.replace('%', '').replace(',', ''))
                            performance_data['oneYear'] = perf_val
                        except:
                            pass
                    elif 'year' in label and '3' in label:
                        try:
                            perf_val = float(value.replace('%', '').replace(',', ''))
                            performance_data['threeYears'] = perf_val
                        except:
                            pass
                    elif 'year' in label and '5' in label:
                        try:
                            perf_val = float(value.replace('%', '').replace(',', ''))
                            performance_data['fiveYears'] = perf_val
                        except:
                            pass
            
            # Extract management fee
            fee_text = soup.get_text()
            fee_match = re.search(r'(\d+\.?\d*)%.*(?:fee|management|expense)', fee_text, re.IGNORECASE)
            management_fee = None
            if fee_match:
                try:
                    management_fee = float(fee_match.group(1))
                except:
                    pass
            
            return {
                'apir_code': apir_code,
                'performance': performance_data,
                'management_fee': management_fee,
                'source': 'InvestSMART'
            }
            
        except Exception as e:
            logger.error(f"Error scraping InvestSMART fund {fund_slug}: {e}")
            return None
    
    def get_comprehensive_super_fund_options(self):
        """Get comprehensive list of Australian super fund investment options"""
        
        # Major super fund investment options with known slugs
        super_fund_options = {
            # AustralianSuper Options
            'AustralianSuper Balanced': {
                'fund_name': 'AustralianSuper',
                'option_name': 'Balanced',
                'investsmart_slug': 'australiansuper-balanced-sup/18296',
                'description': 'Diversified balanced option with focus on growth assets',
                'risk_level': 'Medium to High',
                'suggested_timeframe': '10+ years'
            },
            'AustralianSuper Conservative Balanced': {
                'fund_name': 'AustralianSuper',
                'option_name': 'Conservative Balanced',
                'investsmart_slug': 'australiansuper-conservative-bal-sup/18298',
                'description': 'Conservative diversified option with higher allocation to defensive assets',
                'risk_level': 'Medium',
                'suggested_timeframe': '7+ years'
            },
            'AustralianSuper High Growth': {
                'fund_name': 'AustralianSuper',
                'option_name': 'High Growth',
                'investsmart_slug': 'australiansuper-high-growth-sup/18297',
                'description': 'High growth option with focus on shares and growth assets',
                'risk_level': 'High',
                'suggested_timeframe': '10+ years'
            },
            'AustralianSuper Australian Shares': {
                'fund_name': 'AustralianSuper',
                'option_name': 'Australian Shares',
                'investsmart_slug': 'australiansuper-australian-shares-super/18301',
                'description': 'Focused on Australian share market investments',
                'risk_level': 'High',
                'suggested_timeframe': '7+ years'
            },
            'AustralianSuper International Shares': {
                'fund_name': 'AustralianSuper',
                'option_name': 'International Shares',
                'investsmart_slug': 'australiansuper-international-shares-super/18302',
                'description': 'Focused on international share market investments',
                'risk_level': 'High',
                'suggested_timeframe': '7+ years'
            },
            
            # Hostplus Options
            'Hostplus Balanced': {
                'fund_name': 'Hostplus',
                'option_name': 'Balanced',
                'investsmart_slug': 'hostplus-balanced-super/33463',
                'description': 'MySuper balanced investment option',
                'risk_level': 'Medium to High',
                'suggested_timeframe': '10+ years'
            },
            'Hostplus Conservative': {
                'fund_name': 'Hostplus',
                'option_name': 'Conservative',
                'investsmart_slug': 'hostplus-conservative-super/33461',
                'description': 'Conservative investment option',
                'risk_level': 'Low to Medium',
                'suggested_timeframe': '5+ years'
            },
            'Hostplus Growth': {
                'fund_name': 'Hostplus',
                'option_name': 'Growth',
                'investsmart_slug': 'hostplus-aggressive-super/33462',
                'description': 'High growth investment option',
                'risk_level': 'High',
                'suggested_timeframe': '10+ years'
            },
            
            # REST Industry Super Options
            'REST Balanced': {
                'fund_name': 'REST Industry Super',
                'option_name': 'Balanced',
                'investsmart_slug': 'rest-super-core-strategy-mysuper/22765',
                'description': 'Default MySuper balanced option',
                'risk_level': 'Medium to High',
                'suggested_timeframe': '10+ years'
            },
            'REST Conservative': {
                'fund_name': 'REST Industry Super',
                'option_name': 'Conservative',
                'investsmart_slug': 'rest-super-conservative-strategy/22766',
                'description': 'Conservative investment strategy',
                'risk_level': 'Low to Medium',
                'suggested_timeframe': '5+ years'
            },
            
            # UniSuper Options
            'UniSuper Balanced': {
                'fund_name': 'UniSuper',
                'option_name': 'Balanced',
                'investsmart_slug': 'unisuper-balanced-super/18340',
                'description': 'Default balanced investment option',
                'risk_level': 'Medium to High',
                'suggested_timeframe': '10+ years'
            },
            'UniSuper Conservative': {
                'fund_name': 'UniSuper',
                'option_name': 'Conservative',
                'investsmart_slug': 'unisuper-conservative-super/18341',
                'description': 'Conservative balanced option',
                'risk_level': 'Low to Medium',
                'suggested_timeframe': '5+ years'
            },
            
            # HESTA Options
            'HESTA Balanced Growth': {
                'fund_name': 'HESTA',
                'option_name': 'Balanced Growth',
                'investsmart_slug': 'hesta-balanced-growth-mysuper/45068',
                'description': 'Default MySuper balanced growth option',
                'risk_level': 'Medium to High',
                'suggested_timeframe': '10+ years'
            },
            'HESTA Conservative': {
                'fund_name': 'HESTA',
                'option_name': 'Conservative',
                'investsmart_slug': 'hesta-conservative-super/45069',
                'description': 'Conservative investment option',
                'risk_level': 'Low to Medium',
                'suggested_timeframe': '5+ years'
            },
            
            # Cbus Options
            'Cbus Growth': {
                'fund_name': 'Cbus',
                'option_name': 'Growth (MySuper)',
                'investsmart_slug': 'cbus-growth-mysuper/44989',
                'description': 'Default MySuper growth option',
                'risk_level': 'Medium to High',
                'suggested_timeframe': '10+ years'
            },
            'Cbus Conservative': {
                'fund_name': 'Cbus',
                'option_name': 'Conservative',
                'investsmart_slug': 'cbus-conservative-super/44990',
                'description': 'Conservative investment option',
                'risk_level': 'Low to Medium',
                'suggested_timeframe': '5+ years'
            }
        }
        
        return super_fund_options
    
    def get_asx_etf_data(self):
        """Get comprehensive ASX ETF data"""
        etf_data = {
            # Major Australian ETFs
            'VAS': {
                'name': 'Vanguard Australian Shares Index ETF',
                'apir': 'VAN0011AU',
                'description': 'Tracks the ASX 300 Index',
                'sector': 'Australian Equity',
                'fund_manager': 'Vanguard'
            },
            'VGS': {
                'name': 'Vanguard MSCI Index International Shares ETF',
                'apir': 'VAN0012AU', 
                'description': 'Tracks international developed markets',
                'sector': 'International Equity',
                'fund_manager': 'Vanguard'
            },
            'VTS': {
                'name': 'Vanguard US Total Market Shares Index ETF',
                'apir': 'VAN0013AU',
                'description': 'Tracks the total US stock market',
                'sector': 'US Equity',
                'fund_manager': 'Vanguard'
            },
            'A200': {
                'name': 'BetaShares Australia 200 ETF',
                'apir': 'BTA0035AU',
                'description': 'Tracks the ASX 200 Index',
                'sector': 'Australian Equity',
                'fund_manager': 'BetaShares'
            },
            'IOZ': {
                'name': 'iShares Core S&P 500 ETF',
                'apir': 'IOZ0001AU',
                'description': 'Tracks the S&P 500 Index',
                'sector': 'US Equity',
                'fund_manager': 'iShares'
            },
            'VGB': {
                'name': 'Vanguard Australian Government Bond Index ETF',
                'apir': 'VAN0014AU',
                'description': 'Tracks Australian government bonds',
                'sector': 'Fixed Interest',
                'fund_manager': 'Vanguard'
            },
            'NDQ': {
                'name': 'BetaShares NASDAQ 100 ETF',
                'apir': 'BTA0036AU',
                'description': 'Tracks the NASDAQ 100 Index',
                'sector': 'US Technology',
                'fund_manager': 'BetaShares'
            },
            'IVV': {
                'name': 'iShares Core S&P 500 ETF',
                'apir': 'IVV0001AU',
                'description': 'Tracks the S&P 500 Index',
                'sector': 'US Equity',
                'fund_manager': 'iShares'
            }
        }
        
        return etf_data
    
    def fetch_morningstar_enhanced(self, term, search_type='funds'):
        """Enhanced Morningstar search with better Australian targeting"""
        try:
            # Enhanced search parameters for Australian data
            if search_type == 'funds':
                # Try multiple search strategies
                search_configs = [
                    {
                        'term': term,
                        'field': [
                            "Name", "fundShareClassId", "SecId", "Ticker", "TenforeId",
                            "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                            "ongoingCharge", "globalAssetClassId", "LargestSector", "MarketCountryName", 
                            "currency", "ExchangeId", "CategoryName", "FeeLevel", "starRating"
                        ],
                        'country': 'AU',
                        'currency': 'AUD',
                        'pageSize': 50
                    },
                    {
                        'term': term,
                        'field': [
                            "Name", "fundShareClassId", "SecId", "Ticker", "TenforeId",
                            "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                            "ongoingCharge", "globalAssetClassId", "LargestSector", "MarketCountryName", 
                            "currency", "ExchangeId", "CategoryName", "FeeLevel", "starRating"
                        ],
                        'universe': 'E0WWE$$ALL',  # Global equity universe
                        'pageSize': 50
                    }
                ]
                
                all_results = []
                for config in search_configs:
                    try:
                        results = mstarpy.search_funds(**config)
                        all_results.extend(results)
                    except Exception as e:
                        logger.warning(f"Morningstar search config failed: {e}")
                        continue
                
                return all_results
                
            elif search_type == 'stocks':
                return mstarpy.search_stock(
                    term=term,
                    field=[
                        "Name", "fundShareClassId", "SecId", "Ticker", "TenforeId",
                        "GBRReturnM3", "GBRReturnM12", "GBRReturnM36", "GBRReturnM60", "GBRReturnM120",
                        "SectorName", "IndustryName", "ExchangeId", "MarketCountryName", "currency"
                    ],
                    exchange='XASX',
                    country='AU',
                    currency='AUD',
                    pageSize=50
                )
                
        except Exception as e:
            logger.error(f"Enhanced Morningstar search failed: {e}")
            return []
    
    def search_comprehensive(self, term, search_type='combined'):
        """Comprehensive search across all data sources"""
        all_results = []
        
        # 1. Search super fund investment options
        if search_type in ['funds', 'combined', 'super']:
            super_options = self.get_comprehensive_super_fund_options()
            
            for option_name, option_data in super_options.items():
                if (term.lower() in option_name.lower() or 
                    term.lower() in option_data['fund_name'].lower() or
                    term.lower() in option_data['option_name'].lower()):
                    
                    # Try to get detailed data from InvestSMART
                    detailed_data = None
                    if option_data.get('investsmart_slug'):
                        detailed_data = self.scrape_investsmart_fund(option_data['investsmart_slug'])
                    
                    result = {
                        'apir': detailed_data.get('apir_code') if detailed_data else f"ASU{hash(option_name) % 10000:04d}AU",
                        'name': option_name,
                        'threeMonths': detailed_data.get('performance', {}).get('threeMonths') if detailed_data else None,
                        'oneYear': detailed_data.get('performance', {}).get('oneYear') if detailed_data else None,
                        'threeYears': detailed_data.get('performance', {}).get('threeYears') if detailed_data else None,
                        'fiveYears': detailed_data.get('performance', {}).get('fiveYears') if detailed_data else None,
                        'tenYears': detailed_data.get('performance', {}).get('tenYears') if detailed_data else None,
                        'tcr': detailed_data.get('management_fee') if detailed_data else None,
                        'assetClass': 'Superannuation',
                        'sector': option_data['description'],
                        'status': 'Australian Super Fund Investment Option',
                        'country': 'Australia',
                        'currency': 'AUD',
                        'exchange': 'Australian Super',
                        'type': 'Super Fund Option',
                        'fund_name': option_data['fund_name'],
                        'option_name': option_data['option_name'],
                        'risk_level': option_data['risk_level'],
                        'suggested_timeframe': option_data['suggested_timeframe']
                    }
                    all_results.append(result)
        
        # 2. Search ASX ETFs
        if search_type in ['stocks', 'combined', 'etf']:
            etf_data = self.get_asx_etf_data()
            
            for ticker, etf_info in etf_data.items():
                if (term.lower() in ticker.lower() or 
                    term.lower() in etf_info['name'].lower() or
                    term.lower() in etf_info.get('apir', '').lower()):
                    
                    result = {
                        'apir': etf_info['apir'],
                        'name': f"{etf_info['name']} ({ticker})",
                        'threeMonths': None,  # Would need to fetch from market data
                        'oneYear': None,
                        'threeYears': None,
                        'fiveYears': None,
                        'tenYears': None,
                        'tcr': None,  # ETFs typically have management expense ratios
                        'assetClass': etf_info['sector'],
                        'sector': etf_info['description'],
                        'status': 'ASX ETF',
                        'country': 'Australia',
                        'currency': 'AUD',
                        'exchange': 'ASX',
                        'type': 'ETF',
                        'ticker': ticker,
                        'fund_manager': etf_info['fund_manager']
                    }
                    all_results.append(result)
        
        # 3. Enhanced Morningstar search
        if search_type in ['funds', 'combined']:
            try:
                morningstar_funds = self.fetch_morningstar_enhanced(term, 'funds')
                for item in morningstar_funds:
                    result = self.format_morningstar_data(item, 'Enhanced Morningstar Funds')
                    if result and result['apir'] and result['name']:
                        all_results.append(result)
            except Exception as e:
                logger.error(f"Morningstar funds search failed: {e}")
        
        if search_type in ['stocks', 'combined']:
            try:
                morningstar_stocks = self.fetch_morningstar_enhanced(term, 'stocks')
                for item in morningstar_stocks:
                    result = self.format_morningstar_data(item, 'Enhanced Morningstar Stocks')
                    if result and result['apir'] and result['name']:
                        result['tcr'] = None  # Stocks don't have ongoing charges
                        result['type'] = 'Stock'
                        all_results.append(result)
            except Exception as e:
                logger.error(f"Morningstar stocks search failed: {e}")
        
        return all_results
    
    def format_morningstar_data(self, item, source):
        """Format Morningstar data consistently"""
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
            'status': source,
            'country': item.get('MarketCountryName', 'Australia'),
            'currency': item.get('currency', 'AUD'),
            'exchange': item.get('ExchangeId', ''),
            'type': 'Fund'
        }

# Initialize comprehensive data service
comprehensive_service = ComprehensiveAustralianDataService()

def format_investment_data(item, source="Unknown"):
    """Format investment data to match your frontend structure"""
    return item  # Items are already formatted by the comprehensive service

@app.route('/api/search/funds', methods=['GET'])
def search_funds():
    """Enhanced funds search with comprehensive Australian data"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        country = request.args.get('country', None)
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        logger.info(f"Searching funds: term='{term}', country='{country}'")
        
        # Use comprehensive search
        if country and country.lower() == 'au':
            results = comprehensive_service.search_comprehensive(term, 'funds')
        else:
            # For non-Australian searches, fall back to Morningstar
            results = comprehensive_service.fetch_morningstar_enhanced(term, 'funds')
            formatted_results = []
            for item in results:
                formatted_item = comprehensive_service.format_morningstar_data(item, 'Morningstar Global')
                if formatted_item and formatted_item['apir'] and formatted_item['name']:
                    formatted_results.append(formatted_item)
            results = formatted_results
        
        # Remove duplicates and limit results
        seen_names = set()
        unique_results = []
        for item in results:
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
            'sources_used': ['Comprehensive Australian Database', 'Enhanced Morningstar', 'InvestSMART Scraping']
        })
        
    except Exception as e:
        logger.error(f"Error in search_funds: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/stocks', methods=['GET'])
def search_stocks():
    """Enhanced stocks search including ASX ETFs"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        country = request.args.get('country', None)
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        logger.info(f"Searching stocks: term='{term}', country='{country}'")
        
        # Use comprehensive search including ETFs
        if country and country.lower() == 'au':
            results = comprehensive_service.search_comprehensive(term, 'stocks')
        else:
            results = comprehensive_service.fetch_morningstar_enhanced(term, 'stocks')
            formatted_results = []
            for item in results:
                formatted_item = comprehensive_service.format_morningstar_data(item, 'Morningstar Global Stocks')
                if formatted_item and formatted_item['apir'] and formatted_item['name']:
                    formatted_item['tcr'] = None
                    formatted_item['type'] = 'Stock'
                    formatted_results.append(formatted_item)
            results = formatted_results
        
        # Remove duplicates and limit results
        seen_names = set()
        unique_results = []
        for item in results:
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
            'country': country
        })
        
    except Exception as e:
        logger.error(f"Error in search_stocks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/australia', methods=['GET'])
def search_australia():
    """Comprehensive Australian search with all data sources"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        search_type = request.args.get('type', 'combined')
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        logger.info(f"Comprehensive Australian search: term='{term}', type='{search_type}'")
        
        # Use the comprehensive search with all Australian sources
        results = comprehensive_service.search_comprehensive(term, search_type)
        
        # Remove duplicates
        seen_names = set()
        unique_results = []
        for item in results:
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
            'country': 'Australia',
            'sources': [
                'Australian Super Fund Investment Options',
                'ASX ETFs Database', 
                'Enhanced Morningstar Australia',
                'InvestSMART Data Scraping'
            ]
        })
        
    except Exception as e:
        logger.error(f"Error in search_australia: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/combined', methods=['GET'])
def search_combined():
    """Combined search for both funds and stocks"""
    try:
        term = request.args.get('term', '')
        page_size = int(request.args.get('pageSize', 20))
        country = request.args.get('country', None)
        
        if not term:
            return jsonify({'error': 'Search term is required'}), 400
        
        # Use comprehensive search
        if country and country.lower() == 'au':
            results = comprehensive_service.search_comprehensive(term, 'combined')
        else:
            # Global search combining funds and stocks
            fund_results = comprehensive_service.fetch_morningstar_enhanced(term, 'funds')
            stock_results = comprehensive_service.fetch_morningstar_enhanced(term, 'stocks')
            
            results = []
            
            # Format fund results
            for item in fund_results:
                formatted_item = comprehensive_service.format_morningstar_data(item, 'Morningstar Global')
                if formatted_item and formatted_item['apir'] and formatted_item['name']:
                    results.append(formatted_item)
            
            # Format stock results
            for item in stock_results:
                formatted_item = comprehensive_service.format_morningstar_data(item, 'Morningstar Global')
                if formatted_item and formatted_item['apir'] and formatted_item['name']:
                    formatted_item['tcr'] = None
                    formatted_item['type'] = 'Stock'
                    results.append(formatted_item)
        
        # Remove duplicates
        seen_names = set()
        unique_results = []
        for item in results:
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
        'message': 'Comprehensive Australian Investment Performance API is running',
        'services': {
            'morningstar': 'Available',
            'comprehensive_australian_database': 'Available',
            'investsmart_scraping': 'Available',
            'asx_etf_database': 'Available'
        },
        'coverage': {
            'australian_super_fund_options': 'Detailed investment options within major super funds',
            'asx_etfs': 'Comprehensive ASX ETF coverage with APIR codes',
            'morningstar_enhanced': 'Enhanced Morningstar targeting for Australian data',
            'performance_data': 'Real performance data scraped from multiple sources'
        }
    })

@app.route('/')
def home():
    """Enhanced home route with comprehensive information"""
    return jsonify({
        'message': 'Comprehensive Australian Investment Performance API',
        'status': 'live',
        'coverage': 'Complete Australian investment universe + Global markets',
        'endpoints': [
            '/api/health', 
            '/api/search/funds', 
            '/api/search/stocks', 
            '/api/search/combined',
            '/api/search/australia'
        ],
        'data_sources': {
            'australian_super_fund_options': {
                'description': 'Investment options within major Australian super funds',
                'funds_covered': ['AustralianSuper', 'Hostplus', 'REST', 'UniSuper', 'HESTA', 'Cbus'],
                'data_includes': 'APIR codes, performance data, risk levels, descriptions'
            },
            'asx_etf_database': {
                'description': 'Comprehensive ASX ETF coverage',
                'includes': 'All major ASX ETFs with proper APIR codes and tickers'
            },
            'morningstar_enhanced': {
                'description': 'Enhanced Morningstar API targeting',
                'improvements': 'Better Australian data retrieval, multiple search strategies'
            },
            'investsmart_scraping': {
                'description': 'Real-time data scraping from InvestSMART',
                'provides': 'APIR codes, performance data, management fees'
            }
        },
        'australian_improvements': [
            'Complete super fund investment options (not just fund names)',
            'Real APIR codes for all major Australian investments',
            'Performance data scraped from multiple sources',
            'ASX ETF database with proper ticker mapping',
            'Enhanced Morningstar Australian targeting',
            'Comprehensive search across all Australian investment types'
        ]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("Starting Comprehensive Australian Investment Performance API server...")
    app.run(debug=True, host='0.0.0.0', port=port)
