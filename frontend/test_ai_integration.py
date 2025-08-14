"""
Test Script per AI Trading Integration

Questo script testa l'integrazione AI senza eseguire trade reali
"""
import sys
import os
import time
from datetime import datetime

# Aggiungi il path per importare i moduli
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ai_imports():
    """Test import dei moduli AI"""
    print("🧪 Testing AI Module Imports...")
    
    try:
        from ai_modules.ai_trading_manager import AITradingManager
        print("✅ AITradingManager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import AITradingManager: {e}")
        return False
    
    try:
        from ai_modules.ai_config import AIConfig
        print("✅ AIConfig imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import AIConfig: {e}")
        return False
    
    try:
        from ai_modules.news_analyzer import NewsAnalyzer
        print("✅ NewsAnalyzer imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import NewsAnalyzer: {e}")
        return False
    
    try:
        from ai_modules.macro_analyzer import MacroAnalyzer
        print("✅ MacroAnalyzer imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import MacroAnalyzer: {e}")
        return False
    
    try:
        from ai_modules.openai_engine import OpenAIDecisionEngine
        print("✅ OpenAIDecisionEngine imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import OpenAIDecisionEngine: {e}")
        return False
    
    return True

def test_ai_config():
    """Test configurazione AI"""
    print("\n🧪 Testing AI Configuration...")
    
    try:
        from ai_modules.ai_config import AIConfig
        config = AIConfig()
        
        print(f"📊 Technical Weight: {config.TECHNICAL_WEIGHT}")
        print(f"📰 Sentiment Weight: {config.SENTIMENT_WEIGHT}")
        print(f"🌍 Fundamental Weight: {config.FUNDAMENTAL_WEIGHT}")
        print(f"🎯 Min Confidence: {config.MIN_CONFIDENCE}")
        
        # Test validation
        missing_keys = config.validate_api_keys()
        if missing_keys:
            print(f"⚠️ Missing API Keys: {missing_keys}")
            print("💡 Add these to your .env file for full functionality")
        else:
            print("✅ All API keys configured")
        
        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_ai_manager():
    """Test AI Trading Manager"""
    print("\n🧪 Testing AI Trading Manager...")
    
    try:
        from ai_modules.ai_trading_manager import AITradingManager
        
        # Create mock trading bot
        class MockTradingBot:
            def get_technical_analysis(self, symbol):
                return {
                    'ema_trend': 'bullish',
                    'current_price': 45000.0,
                    'candles_above_ema': 5,
                    'candles_below_ema': 2,
                    'volatility': 2.5,
                    'volume_analysis': 'high',
                    'last_updated': datetime.now().isoformat()
                }
        
        mock_bot = MockTradingBot()
        ai_manager = AITradingManager(trading_bot_instance=mock_bot)
        
        print("✅ AITradingManager created successfully")
        
        # Test validation
        validation = ai_manager.validate_configuration()
        print(f"📋 Configuration valid: {validation['is_valid']}")
        
        if not validation['is_valid']:
            print(f"⚠️ Missing: {validation['missing_keys']}")
        
        # Test status
        status = ai_manager.get_ai_status()
        print(f"🔄 AI Running: {status['is_running']}")
        print(f"📦 Cache Size: {status['cache_size']}")
        
        return True
    except Exception as e:
        print(f"❌ AI Manager test failed: {e}")
        return False

def test_mock_analysis():
    """Test analisi AI con dati mock"""
    print("\n🧪 Testing AI Analysis with Mock Data...")
    
    try:
        from ai_modules.ai_trading_manager import AITradingManager
        
        # Mock bot con dati realistici
        class DetailedMockBot:
            def get_technical_analysis(self, symbol):
                return {
                    'ema_trend': 'bullish',
                    'current_price': 67500.0,
                    'ema_value': 66800.0,
                    'candles_above_ema': 7,
                    'candles_below_ema': 3,
                    'volatility': 3.2,
                    'volume_analysis': 'above_average',
                    'last_updated': datetime.now().isoformat(),
                    'symbol': symbol
                }
        
        mock_bot = DetailedMockBot()
        ai_manager = AITradingManager(trading_bot_instance=mock_bot)
        
        print("🔍 Running analysis for BTCUSDT...")
        start_time = time.time()
        
        # Esegui analisi
        analysis = ai_manager.analyze_market_conditions("BTCUSDT")
        
        end_time = time.time()
        analysis_time = end_time - start_time
        
        print(f"⏱️ Analysis completed in {analysis_time:.2f} seconds")
        
        # Mostra risultati
        if 'error' in analysis:
            print(f"❌ Analysis error: {analysis['error']}")
            return False
        
        final_decision = analysis.get('final_decision', {})
        print(f"\n📊 AI ANALYSIS RESULTS:")
        print(f"🎯 Decision: {final_decision.get('action', 'N/A')}")
        print(f"💯 Confidence: {final_decision.get('confidence', 0)}%")
        print(f"💭 Reasoning: {final_decision.get('reasoning', 'N/A')}")
        
        # Technical analysis
        tech_analysis = analysis.get('technical_analysis', {})
        print(f"\n📈 TECHNICAL ANALYSIS:")
        print(f"📊 EMA Trend: {tech_analysis.get('ema_trend', 'N/A')}")
        print(f"💰 Current Price: ${tech_analysis.get('current_price', 0):,.2f}")
        print(f"📊 Volatility: {tech_analysis.get('volatility', 0)}%")
        
        # News analysis (se disponibile)
        news_analysis = analysis.get('news_analysis', {})
        if 'error' not in news_analysis:
            sentiment = news_analysis.get('sentiment_analysis', {})
            print(f"\n📰 NEWS ANALYSIS:")
            print(f"😊 Sentiment: {sentiment.get('overall_sentiment', 'N/A')}")
            print(f"📊 Score: {sentiment.get('score', 'N/A')}")
        else:
            print(f"\n📰 NEWS ANALYSIS: ⚠️ {news_analysis.get('error', 'Not available')}")
        
        # Macro analysis (se disponibile)
        macro_analysis = analysis.get('macro_analysis', {})
        if 'error' not in macro_analysis:
            print(f"\n🌍 MACRO ANALYSIS:")
            indicators = macro_analysis.get('indicators', {})
            for indicator, value in indicators.items():
                print(f"📊 {indicator}: {value}")
        else:
            print(f"\n🌍 MACRO ANALYSIS: ⚠️ {macro_analysis.get('error', 'Not available')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Mock analysis test failed: {e}")
        return False

def test_api_keys_status():
    """Test status delle API keys"""
    print("\n🧪 Testing API Keys Status...")
    
    api_keys = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'NEWS_API_KEY': os.getenv('NEWS_API_KEY'),
        'CRYPTOPANIC_TOKEN': os.getenv('CRYPTOPANIC_TOKEN'),
        'ALPHA_VANTAGE_KEY': os.getenv('ALPHA_VANTAGE_KEY'),
        'FRED_API_KEY': os.getenv('FRED_API_KEY')
    }
    
    for key_name, key_value in api_keys.items():
        if key_value:
            masked_key = key_value[:8] + '*' * (len(key_value) - 8) if len(key_value) > 8 else '***'
            print(f"✅ {key_name}: {masked_key}")
        else:
            status = "❌ REQUIRED" if key_name == 'OPENAI_API_KEY' else "⚠️ Optional"
            print(f"{status} {key_name}: Not set")
    
    return True

def main():
    """Esegui tutti i test"""
    print("🚀 AI Trading Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_ai_imports),
        ("Config Test", test_ai_config),
        ("AI Manager Test", test_ai_manager),
        ("API Keys Status", test_api_keys_status),
        ("Mock Analysis Test", test_mock_analysis),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} CRASHED: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! AI integration is ready.")
    elif passed >= total - 1:
        print("⚠️ Minor issues detected. Check API keys configuration.")
    else:
        print("❌ Major issues detected. Check installation and configuration.")
    
    print("\n💡 Next Steps:")
    print("1. Configure missing API keys in .env file")
    print("2. Start the dashboard: python app.py")
    print("3. Navigate to: http://localhost:5000/ai-trading")
    print("4. Test AI system in the web interface")

if __name__ == "__main__":
    main()
